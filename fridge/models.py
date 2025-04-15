from django.db import models
from django.contrib.auth.models import User
from recipes.models import Ingredient, MeasurementUnit
from recipes.utils import convert_units
from django.utils import timezone
from datetime import date, timedelta
import logging

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
        Zawsze konwertuje do jednostek podstawowych: gramy (g) dla produktów stałych i mililitry (ml) dla płynów.
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
            
        # Określ podstawową jednostkę dla składnika
        from recipes.models import MeasurementUnit
        
        # Najpierw sprawdź czy składnik ma określony typ jednostki
        unit_type = 'weight'  # domyślnie zakładamy wagę
        if ingredient.unit_type.startswith('volume'):
            unit_type = 'volume'
        
        # Pobierz jednostkę podstawową
        if unit_type == 'weight':
            base_unit = MeasurementUnit.objects.get(symbol='g')
        else:
            base_unit = MeasurementUnit.objects.get(symbol='ml')
        
        # Dodajemy dodatkowe logowanie do debugowania
        logger = logging.getLogger(__name__)
        logger.info(f"Dodawanie do lodówki: {amount} {unit.symbol} składnika {ingredient.name}")
        logger.info(f"Typ jednostki: {unit.type}, Typ podstawowy: {unit_type}")
        
        if unit.type == 'piece' and 'piece' in ingredient.unit_type:
            # Sprawdzenie wagi sztuki
            if not ingredient.piece_weight:
                logger.error(f"BŁĄD: Brak wagi sztuki dla {ingredient.name}")
            else:
                logger.info(f"Waga sztuki dla {ingredient.name}: {ingredient.piece_weight}g")
        
        # Jeśli jednostka już jest podstawowa, nie ma potrzeby konwersji
        original_amount = amount
        original_unit = unit
        
        if unit != base_unit:
            try:
                # Spróbuj przekonwertować do jednostki podstawowej
                from recipes.utils import convert_units
                
                # Dodatkowe logowanie przed konwersją
                logger.info(f"Próba konwersji z {unit.symbol} na {base_unit.symbol} dla {ingredient.name}")
                
                amount = convert_units(amount, unit, base_unit, ingredient=ingredient)
                
                # Dodatkowe logowanie po konwersji
                logger.info(f"Po konwersji: {amount} {base_unit.symbol}")
                
                unit = base_unit
            except Exception as e:
                # W przypadku błędu konwersji, zachowaj oryginalną jednostkę
                logger.error(f"Nie można przekonwertować {original_amount} {original_unit} na {base_unit}: {str(e)}")
                # Ale nadal próbujemy dodać produkt z oryginalną jednostką
        
        # Szukaj istniejącego wpisu z tą samą jednostką podstawową i datą ważności
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
            return existing, original_unit != unit
        else:
            # Utwórz nowy wpis
            new_item = cls.objects.create(
                user=user,
                ingredient=ingredient,
                amount=amount,
                unit=unit,
                expiry_date=expiry_date
            )
            return new_item, original_unit != unit
    
    @classmethod
    def consolidate_fridge_items(cls, user):
        """
        Konsoliduje wszystkie produkty w lodówce, łącząc te same składniki
        i konwertując je do jednostek podstawowych.
        
        Zwraca liczbę skonsolidowanych produktów.
        """
        from django.db.models import Count
        from recipes.utils import convert_units
        from recipes.models import MeasurementUnit
        
        # Pobierz podstawowe jednostki
        try:
            gram_unit = MeasurementUnit.objects.get(symbol='g')
            ml_unit = MeasurementUnit.objects.get(symbol='ml')
        except MeasurementUnit.DoesNotExist:
            raise ValueError("Podstawowe jednostki (g/ml) nie istnieją w bazie danych")
        
        # Pobierz wszystkie składniki z lodówki użytkownika
        ingredients_groups = cls.objects.filter(user=user).values('ingredient_id').distinct()
        consolidated_count = 0
        
        # Dla każdego unikalnego składnika
        for ing_data in ingredients_groups:
            ingredient_id = ing_data['ingredient_id']
            
            # Pobierz wszystkie wpisy dla tego składnika
            items = cls.objects.filter(
                user=user,
                ingredient_id=ingredient_id
            ).select_related('ingredient', 'unit').order_by('expiry_date')
            
            if not items:
                continue
                
            # Określ podstawową jednostkę dla tego składnika
            first_item = items[0]
            unit_type = 'weight'  # domyślnie zakładamy wagę
            if first_item.ingredient.unit_type.startswith('volume'):
                unit_type = 'volume'
                base_unit = ml_unit
            else:
                base_unit = gram_unit
            
            # Znajdź wszystkie unikalne daty ważności dla tego składnika
            expiry_dates = set()
            for item in items:
                if item.expiry_date:
                    expiry_dates.add(item.expiry_date)
                else:
                    # Dodaj None jako osobną "datę" (brak daty)
                    expiry_dates.add(None)
            
            # Dla każdej unikalnej daty ważności
            for expiry_date in expiry_dates:
                date_items = items.filter(expiry_date=expiry_date)
                
                if date_items.count() <= 1 and date_items.first().unit == base_unit:
                    continue  # nie ma potrzeby konsolidacji jeśli jest tylko jeden wpis i już ma podstawową jednostkę
                
                # Skonsoliduj do jednego wpisu
                total_amount = 0
                for item in date_items:
                    try:
                        # Konwertuj do jednostki podstawowej i dodaj
                        if item.unit != base_unit:
                            converted = convert_units(item.amount, item.unit, base_unit)
                            total_amount += converted
                        else:
                            total_amount += item.amount
                    except Exception as e:
                        print(f"Błąd konwersji dla {item.ingredient.name}: {str(e)}")
                        # Jeśli konwersja się nie powiedzie, po prostu dodaj ilość (lepsze niż utrata danych)
                        # To może nie być idealnie dokładne, ale pozwala zachować dane
                        total_amount += item.amount
                
                # Usuń oryginalne wpisy
                items_to_delete = list(date_items)  # tworzymy kopię, żeby nie usunąć oryginału przed utworzeniem nowego
                date_items.delete()
                
                # Utwórz nowy skonsolidowany wpis
                cls.objects.create(
                    user=user,
                    ingredient_id=ingredient_id,
                    amount=total_amount,
                    unit=base_unit,
                    expiry_date=expiry_date
                )
                
                consolidated_count += len(items_to_delete) - 1  # odejmujemy 1, bo tworzymy jeden nowy wpis
        
        return consolidated_count
    
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
        Używa produktów według reguły FIFO - najpierw najkrótszy termin ważności.
        
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
                
                # Pobierz dostępne w lodówce produkty dla tego składnika, posortowane po dacie ważności (FIFO)
                fridge_items = cls.objects.filter(
                    user=user,
                    ingredient=ingredient
                ).order_by('expiry_date', 'purchase_date')  # najpierw najkrótszy termin ważności, potem najstarsze zakupy
                
                amount_to_remove = amount_needed
                removed_items = []
                
                for item in fridge_items:
                    # Jeśli już usunęliśmy całą potrzebną ilość, przerwij pętlę
                    if amount_to_remove <= 0:
                        break
                    
                    try:
                        # Jeśli jednostki są różne, przelicz ilość
                        if item.unit != unit:
                            # Konwertuj ilość potrzebną na jednostkę produktu w lodówce
                            converted_amount = convert_units(amount_to_remove, unit, item.unit, ingredient=ingredient)
                        else:
                            converted_amount = amount_to_remove
                            
                        # Zapewnij, że wartości są typu float
                        item_amount = float(item.amount)
                        converted_amount = float(converted_amount)
                            
                        if item_amount > converted_amount:
                            # Mamy wystarczającą ilość w tym produkcie
                            item.amount = item_amount - converted_amount
                            item.save()
                            
                            # Rejestruj użycie - ile i z jakiego produktu
                            removed_items.append({
                                'item': item,
                                'amount': converted_amount,
                                'unit': item.unit
                            })
                            
                            # Zaktualizuj ilość do usunięcia na 0
                            amount_to_remove = 0
                        else:
                            # Zużywamy cały produkt i kontynuujemy usuwanie
                            # Konwertuj z powrotem na jednostkę przepisu
                            if item.unit != unit:
                                amount_removed_in_recipe_unit = convert_units(item_amount, item.unit, unit, ingredient=ingredient)
                            else:
                                amount_removed_in_recipe_unit = item_amount
                            
                            # Odejmij usuniętą ilość od ilości do usunięcia
                            amount_to_remove -= float(amount_removed_in_recipe_unit)
                            
                            # Rejestruj użycie - ile i z jakiego produktu
                            removed_items.append({
                                'item': item,
                                'amount': item_amount,
                                'unit': item.unit,
                                'fully_used': True
                            })
                            
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
                    "unit": unit,
                    "items_used": removed_items
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
        debug_info = []
        
        for item in items:
            try:
                # Jeśli jednostki są różne, przelicz ilość
                if item.unit != unit:
                    try:
                        from recipes.utils import convert_units
                        converted_amount = convert_units(float(item.amount), item.unit, unit, ingredient=ingredient)
                        total_available += converted_amount
                        debug_info.append(f"Konwersja: {item.amount} {item.unit.symbol} -> {converted_amount} {unit.symbol}")
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

class ExpiryNotification(models.Model):
    """Model przechowujący informacje o powiadomieniach dotyczących przeterminowanych produktów"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expiry_notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Powiadomienie o przeterminowaniu"
        verbose_name_plural = "Powiadomienia o przeterminowaniu"
    
    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%d.%m.%Y')})"
    
    @classmethod
    def check_expiring_products(cls, user):
        """
        Sprawdza produkty, które niedługo się przeterminują lub już są przeterminowane
        i generuje odpowiednie powiadomienia.
        
        Args:
            user (User): Użytkownik, dla którego sprawdzane są produkty
            
        Returns:
            int: Liczba wygenerowanych powiadomień
        """
        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        # Produkty przeterminowane, o których użytkownik jeszcze nie został powiadomiony
        expired_items = FridgeItem.objects.filter(
            user=user,
            expiry_date__lt=today
        )
        
        # Produkty, które przeterminują się jutro
        expiring_tomorrow = FridgeItem.objects.filter(
            user=user, 
            expiry_date=tomorrow
        )
        
        # Produkty, które przeterminują się w ciągu tygodnia
        expiring_soon = FridgeItem.objects.filter(
            user=user,
            expiry_date__gt=tomorrow,
            expiry_date__lte=next_week
        )
        
        notifications_count = 0
        
        # Powiadomienie o przeterminowanych produktach
        if expired_items.exists():
            expired_count = expired_items.count()
            items_list = ", ".join([item.ingredient.name for item in expired_items[:5]])
            
            if expired_count > 5:
                items_list += f" i {expired_count - 5} innych"
            
            cls.objects.create(
                user=user,
                title="Przeterminowane produkty",
                message=f"Masz {expired_count} przeterminowanych produktów w lodówce: {items_list}. "
                        f"Zalecamy ich usunięcie."
            )
            notifications_count += 1
        
        # Powiadomienie o produktach, które przeterminują się jutro
        if expiring_tomorrow.exists():
            expiring_count = expiring_tomorrow.count()
            items_list = ", ".join([item.ingredient.name for item in expiring_tomorrow[:5]])
            
            if expiring_count > 5:
                items_list += f" i {expiring_count - 5} innych"
            
            cls.objects.create(
                user=user,
                title="Produkty wygasają jutro",
                message=f"{expiring_count} produktów wygasa jutro: {items_list}. "
                        f"Wykorzystaj je jak najszybciej."
            )
            notifications_count += 1
        
        # Powiadomienie o produktach, które przeterminują się w ciągu tygodnia
        if expiring_soon.exists():
            expiring_count = expiring_soon.count()
            items_list = ", ".join([f"{item.ingredient.name} ({item.days_until_expiry} dni)" for item in expiring_soon[:5]])
            
            if expiring_count > 5:
                items_list += f" i {expiring_count - 5} innych"
            
            cls.objects.create(
                user=user,
                title="Produkty wygasają wkrótce",
                message=f"{expiring_count} produktów wygasa w ciągu tygodnia: {items_list}. "
                        f"Zaplanuj wykorzystanie tych produktów."
            )
            notifications_count += 1
        
        return notifications_count


