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
        scale_factor = servings / recipe.servings
        
        # Sprawdź, czy wszystkie składniki są dostępne
        for ingredient_entry in recipe.ingredients.all():
            ingredient = ingredient_entry.ingredient
            amount_needed = ingredient_entry.amount * scale_factor
            unit = ingredient_entry.unit
            
            # Sprawdź dostępność składnika
            available = cls.check_ingredient_availability(user, ingredient, amount_needed, unit)
            
            if not available:
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
                amount_needed = ingredient_entry.amount * scale_factor
                unit = ingredient_entry.unit
                
                removed = cls.remove_from_fridge(user, ingredient, amount_needed, unit)
                result["used"].append({
                    "ingredient": ingredient,
                    "amount": amount_needed,
                    "unit": unit,
                    "success": removed
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
        items = cls.objects.filter(
            user=user,
            ingredient=ingredient
        )
        
        total_available = 0
        
        for item in items:
            # Jeśli jednostki są różne, przelicz ilość
            if item.unit != unit:
                try:
                    converted_amount = convert_units(item.amount, item.unit, unit)
                    total_available += converted_amount
                except ValueError:
                    # Jeśli konwersja niemożliwa, ignoruj ten produkt
                    pass
            else:
                total_available += item.amount
                
        return total_available >= amount


