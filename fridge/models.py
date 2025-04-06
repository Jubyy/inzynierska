from django.db import models
from django.contrib.auth.models import User
from recipes.models import Ingredient, MeasurementUnit
from recipes.utils import convert_units
from django.utils import timezone
from datetime import date

class FridgeItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fridge_items', verbose_name="Użytkownik")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, verbose_name="Składnik")
    amount = models.FloatField(verbose_name="Ilość")
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, verbose_name="Jednostka")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="Data ważności")
    purchase_date = models.DateField(default=timezone.now, verbose_name="Data zakupu")
    added_date = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    
    class Meta:
        verbose_name = "Produkt w lodówce"
        verbose_name_plural = "Produkty w lodówce"
        unique_together = ('user', 'ingredient', 'unit', 'expiry_date')
        ordering = ['expiry_date', 'ingredient__name']
    
    def __str__(self):
        expiry_info = f" (ważne do {self.expiry_date})" if self.expiry_date else ""
        return f"{self.amount} {self.unit.symbol} {self.ingredient.name}{expiry_info}"
    
    @property
    def is_expired(self):
        """Sprawdza, czy produkt jest przeterminowany"""
        if self.expiry_date:
            return self.expiry_date < date.today()
        return False
    
    @property
    def days_until_expiry(self):
        """Zwraca liczbę dni do przeterminowania"""
        if self.expiry_date:
            delta = self.expiry_date - date.today()
            return delta.days
        return None
    
    def convert_to_unit(self, target_unit):
        """Konwertuje ilość produktu na inną jednostkę"""
        try:
            converted_amount = convert_units(self.amount, self.unit, target_unit)
            return converted_amount
        except ValueError:
            return None
    
    @classmethod
    def add_to_fridge(cls, user, ingredient, amount, unit, expiry_date=None):
        """
        Dodaje produkt do lodówki lub aktualizuje istniejący.
        Jeśli ten sam produkt już istnieje, jego ilość zostanie zwiększona.
        """
        # Sprawdź poprawność danych wejściowych
        if not ingredient:
            raise ValueError("Nie wybrano składnika")
        if not unit:
            raise ValueError("Nie wybrano jednostki miary")
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Ilość musi być większa od zera")
        except (ValueError, TypeError):
            raise ValueError("Nieprawidłowa wartość ilości")
            
        # Sprawdź czy jednostka jest dozwolona dla tego składnika
        allowed_units = list(ingredient.get_allowed_units())
        compatible_units = list(ingredient.compatible_units.all())
        if unit not in allowed_units and unit not in compatible_units:
            # Automatyczna naprawa - dodaj jednostkę do kompatybilnych
            ingredient.compatible_units.add(unit)
            
        # Sprawdź, czy produkt już istnieje w lodówce (o takim samym terminie ważności)
        existing = cls.objects.filter(
            user=user,
            ingredient=ingredient,
            unit=unit,
            expiry_date=expiry_date
        ).first()
        
        if existing:
            # Aktualizuj istniejący wpis
            existing.amount += amount
            existing.save()
            return existing
        else:
            # Utwórz nowy wpis
            return cls.objects.create(
                user=user,
                ingredient=ingredient,
                amount=amount,
                unit=unit,
                expiry_date=expiry_date
            )
    
    @classmethod
    def remove_from_fridge(cls, user, ingredient, amount, unit):
        """
        Usuwa określoną ilość produktu z lodówki.
        Usuwa produkty od najstarszych/najbliższych przeterminowania.
        Zwraca True, jeśli udało się usunąć całą ilość, False w przeciwnym razie.
        """
        # Pobierz wszystkie pasujące produkty z lodówki, posortowane od najstarszych
        items = cls.objects.filter(
            user=user,
            ingredient=ingredient
        ).order_by('expiry_date', 'purchase_date')
        
        if not items:
            return False
        
        amount_to_remove = amount
        
        for item in items:
            # Jeśli jednostki są różne, przelicz ilość
            if item.unit != unit:
                try:
                    converted_amount = convert_units(amount_to_remove, unit, item.unit)
                except ValueError:
                    # Jeśli konwersja niemożliwa, przejdź do następnego produktu
                    continue
            else:
                converted_amount = amount_to_remove
            
            if item.amount > converted_amount:
                # Jeśli w tym produkcie jest więcej niż potrzebujemy, zmniejsz jego ilość
                item.amount -= converted_amount
                item.save()
                return True
            else:
                # Jeśli zużywamy cały produkt, usuń go i odejmij od ilości do usunięcia
                amount_to_remove -= convert_units(item.amount, item.unit, unit)
                item.delete()
                
                # Jeśli usunęliśmy wszystko, zwróć True
                if amount_to_remove <= 0:
                    return True
        
        # Jeśli dotarliśmy tutaj, znaczy to, że nie udało się usunąć całej ilości
        return False
    
    @classmethod
    def use_recipe_ingredients(cls, user, recipe, servings=None):
        """
        Usuwa z lodówki składniki potrzebne do przygotowania przepisu.
        
        Args:
            user (User): Użytkownik
            recipe (Recipe): Przepis
            servings (int, optional): Liczba porcji. Domyślnie używa liczby porcji z przepisu.
            
        Returns:
            dict: Słownik z informacjami o usuniętych składnikach i ewentualnych brakach
        """
        result = {"success": True, "missing": [], "used": []}
        
        # Jeśli nie podano liczby porcji, użyj domyślnej z przepisu
        if not servings:
            servings = recipe.servings
            
        # Oblicz współczynnik skalowania
        scale_factor = float(servings) / float(recipe.servings)
        
        # Import funkcji konwersji jednostek
        from recipes.utils import convert_units
        
        # Sprawdź, czy wszystkie składniki są dostępne w wystarczającej ilości
        for ingredient_entry in recipe.ingredients.all():
            ingredient = ingredient_entry.ingredient
            amount_needed = float(ingredient_entry.amount) * scale_factor
            unit = ingredient_entry.unit
            
            # Sprawdź dostępność składnika
            if not cls.check_ingredient_availability(user, ingredient, amount_needed, unit):
                result["success"] = False
                result["missing"].append({
                    "ingredient": ingredient,
                    "amount_needed": amount_needed,
                    "unit": unit
                })
        
        # Jeśli wszystkie składniki są dostępne, usuń je z lodówki
        if result["success"]:
            for ingredient_entry in recipe.ingredients.all():
                ingredient = ingredient_entry.ingredient
                amount_needed = float(ingredient_entry.amount) * scale_factor
                unit = ingredient_entry.unit
                
                # Pobierz dostępne w lodówce produkty dla tego składnika
                fridge_items = cls.objects.filter(
                    user=user,
                    ingredient=ingredient
                ).order_by('expiry_date', 'purchase_date')
                
                amount_to_remove = amount_needed
                
                for item in fridge_items:
                    # Jeśli już usunęliśmy całą potrzebną ilość, przerwij pętlę
                    if amount_to_remove <= 0:
                        break
                    
                    try:
                        # Jeśli jednostki są różne, przelicz ilość
                        if item.unit != unit:
                            # Konwertuj ilość potrzebną na jednostkę produktu w lodówce
                            converted_amount = convert_units(amount_to_remove, unit, item.unit)
                        else:
                            converted_amount = amount_to_remove
                            
                        # Zapewnij, że wartości są typu float
                        item_amount = float(item.amount)
                        converted_amount = float(converted_amount)
                            
                        if item_amount > converted_amount:
                            # Mamy wystarczającą ilość w tym produkcie
                            item.amount = item_amount - converted_amount
                            item.save()
                            
                            # Zaktualizuj ilość do usunięcia na 0
                            amount_to_remove = 0
                        else:
                            # Zużywamy cały produkt i kontynuujemy usuwanie
                            # Konwertuj z powrotem na jednostkę przepisu
                            if item.unit != unit:
                                amount_removed_in_recipe_unit = convert_units(item_amount, item.unit, unit)
                            else:
                                amount_removed_in_recipe_unit = item_amount
                            
                            # Odejmij usuniętą ilość od ilości do usunięcia
                            amount_to_remove -= float(amount_removed_in_recipe_unit)
                            
                            # Usuń produkt z lodówki
                            item.delete()
                    except Exception as e:
                        # W przypadku błędu konwersji, przejdź do następnego produktu
                        print(f"Błąd podczas usuwania składnika {ingredient.name}: {e}")
                        continue
                
                # Dodaj informację o zużytym składniku do wyniku
                result["used"].append({
                    "ingredient": ingredient,
                    "amount": amount_needed,
                    "unit": unit
                })
        
        return result
    
    @classmethod
    def check_ingredient_availability(cls, user, ingredient, amount, unit):
        """
        Sprawdza, czy dany składnik jest dostępny w wystarczającej ilości.
        
        Args:
            user (User): Użytkownik
            ingredient (Ingredient): Składnik
            amount (float): Potrzebna ilość
            unit (MeasurementUnit): Jednostka
            
        Returns:
            bool: True jeśli składnik jest dostępny, False w przeciwnym razie
        """
        if not user or not user.is_authenticated:
            return False
        
        if amount <= 0:
            # Jeśli nie potrzebujemy składnika, to jest dostępny
            return True
        
        # Sprawdź czy jednostka jest określona
        if not unit:
            return False
        
        items = cls.objects.filter(
            user=user,
            ingredient=ingredient
        )
        
        if not items.exists():
            # Brak składnika w lodówce
            return False
        
        total_available = 0.0
        
        for item in items:
            try:
                # Jeśli jednostki są różne, przelicz ilość
                if item.unit != unit:
                    try:
                        from recipes.utils import convert_units
                        converted_amount = convert_units(float(item.amount), item.unit, unit)
                        total_available += converted_amount
                    except (ValueError, TypeError) as e:
                        # Logowanie błędu dla debugowania
                        print(f"Błąd konwersji: {e} dla {item.ingredient.name} z {item.unit} na {unit}")
                        # Ignoruj ten produkt, jeśli konwersja nie jest możliwa
                        continue
                else:
                    total_available += float(item.amount)
            except Exception as e:
                # W przypadku nieoczekiwanego błędu, ignoruj ten produkt
                print(f"Nieoczekiwany błąd: {e}")
                continue
            
        # Porównanie dostępnej ilości z potrzebną ilością
        return total_available >= float(amount)


