from django.db import models
from django.contrib.auth.models import User
from recipes.models import Ingredient, MeasurementUnit
from recipes.utils import convert_units
from django.utils import timezone
from datetime import date, timedelta
import logging
import math

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
    
    def get_amount_display(self):
        """
        Zwraca ilość produktu odpowiednio sformatowaną:
        - dla jednostek 'piece' zaokrągloną do góry do liczby całkowitej
        - dla pozostałych jednostek oryginalną wartość z ograniczoną precyzją
        """
        if self.unit.type == 'piece':
            return math.ceil(self.amount)
        # Dla innych jednostek pokazuj maksymalnie 1 miejsce po przecinku, gdy to potrzebne
        amount = float(self.amount)
        if amount == int(amount):
            return int(amount)
        return round(amount, 1)
    
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
        Zawsze konwertuje do jednostek podstawowych lub najlepiej pasujących.
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
            
        # Ustawienie logowania
        logger = logging.getLogger(__name__)
        logger.info(f"Dodawanie do lodówki: {amount} {unit.symbol} składnika {ingredient.name}")
        
        # Określ podstawową jednostkę dla składnika
        from recipes.models import MeasurementUnit
        
        # Zachowaj oryginalną jednostkę i ilość
        original_amount = amount
        original_unit = unit
        
        # Najpierw sprawdź czy składnik ma określony typ jednostki
        unit_type = 'weight'  # domyślnie zakładamy wagę
        if ingredient.unit_type.startswith('volume'):
            unit_type = 'volume'
        
        logger.info(f"Typ jednostki składnika: {ingredient.unit_type}, Typ używany: {unit_type}")
        
        # Pobierz jednostkę podstawową
        if unit_type == 'weight':
            base_unit = MeasurementUnit.objects.get(symbol='g')
        else:
            base_unit = MeasurementUnit.objects.get(symbol='ml')
        
        converted = False
        
        # Nie konwertuj, jeśli jednostka to sztuka (piece) i składnik obsługuje sztuki
        if unit.type == 'piece' and 'piece' in ingredient.unit_type:
            logger.info(f"Używamy jednostki sztukowej dla {ingredient.name}")
            # Nie konwertuj sztuk do wagi, jeśli składnik może być mierzony w sztukach
            pass
        # Nie konwertuj, jeśli jednostka już jest podstawowa
        elif unit == base_unit:
            logger.info(f"Jednostka {unit.symbol} już jest podstawowa")
            pass
        else:
            try:
                # Spróbuj przekonwertować do jednostki podstawowej
                from recipes.utils import convert_units
                
                # Dodatkowe logowanie przed konwersją
                logger.info(f"Próba konwersji z {unit.symbol} na {base_unit.symbol} dla {ingredient.name}")
                
                amount = convert_units(amount, unit, base_unit, ingredient=ingredient)
                
                # Dodatkowe logowanie po konwersji
                logger.info(f"Po konwersji: {amount} {base_unit.symbol}")
                
                unit = base_unit
                converted = True
            except Exception as e:
                # W przypadku błędu konwersji, zachowaj oryginalną jednostkę
                logger.error(f"Nie można przekonwertować {original_amount} {original_unit.symbol} na {base_unit.symbol}: {str(e)}")
                # Zachowujemy oryginalną jednostkę
                amount = original_amount
                unit = original_unit
        
        # Szukaj istniejącego wpisu z tą samą jednostką i datą ważności
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
            logger.info(f"Zaktualizowano istniejący wpis: {existing}")
            return existing, converted
        else:
            # Utwórz nowy wpis
            new_item = cls.objects.create(
                user=user,
                ingredient=ingredient,
                amount=amount,
                unit=unit,
                expiry_date=expiry_date
            )
            logger.info(f"Utworzono nowy wpis: {new_item}")
            return new_item, converted
    
    @classmethod
    def remove_from_fridge(cls, user, ingredient, amount, unit):
        """
        Usuwa określoną ilość produktu z lodówki.
        Usuwa produkty od najstarszych/najbliższych przeterminowania.
        Zwraca True, jeśli udało się usunąć całą ilość, False w przeciwnym razie.
        """
        # Inicjalizacja loggera
        logger = logging.getLogger(__name__)
        logger.info(f"Usuwanie z lodówki: {amount} {unit.symbol} składnika {ingredient.name}")
        
        # Pobierz wszystkie pasujące produkty z lodówki, posortowane od najstarszych
        items = cls.objects.filter(
            user=user,
            ingredient=ingredient
        ).order_by('expiry_date', 'purchase_date')
        
        if not items:
            logger.info(f"Brak produktu {ingredient.name} w lodówce")
            return False
        
        amount_to_remove = float(amount)
        
        for item in items:
            # Jeśli jednostki są różne, przelicz ilość
            if item.unit != unit:
                try:
                    from recipes.utils import convert_units
                    converted_amount = convert_units(amount_to_remove, unit, item.unit, ingredient=ingredient)
                    logger.info(f"Konwersja dla usuwania: {amount_to_remove} {unit.symbol} = {converted_amount} {item.unit.symbol}")
                except ValueError as e:
                    # Jeśli konwersja niemożliwa, przejdź do następnego produktu
                    logger.error(f"Błąd konwersji: {e} dla {ingredient.name}")
                    continue
            else:
                converted_amount = amount_to_remove
            
            if item.amount > converted_amount:
                # Jeśli w tym produkcie jest więcej niż potrzebujemy, zmniejsz jego ilość
                item.amount -= converted_amount
                item.save()
                logger.info(f"Zaktualizowano ilość produktu {ingredient.name} na {item.amount} {item.unit.symbol}")
                return True
            else:
                # Jeśli zużywamy cały produkt, usuń go i odejmij od ilości do usunięcia
                current_amount = float(item.amount)
                if item.unit != unit:
                    try:
                        from recipes.utils import convert_units
                        amount_removed = convert_units(current_amount, item.unit, unit, ingredient=ingredient)
                        amount_to_remove -= amount_removed
                        logger.info(f"Usunięto cały produkt {ingredient.name} ({current_amount} {item.unit.symbol} = {amount_removed} {unit.symbol})")
                    except ValueError as e:
                        logger.error(f"Błąd konwersji odwrotnej: {e} dla {ingredient.name}")
                        continue
                else:
                    amount_to_remove -= current_amount
                    logger.info(f"Usunięto cały produkt {ingredient.name} ({current_amount} {unit.symbol})")
                
                item.delete()
                
                # Jeśli usunęliśmy wszystko, zwróć True
                if amount_to_remove <= 0:
                    return True
        
        # Jeśli dotarliśmy tutaj, znaczy to, że nie udało się usunąć całej ilości
        logger.warning(f"Nie udało się usunąć całej żądanej ilości {ingredient.name}. Pozostało {amount_to_remove} {unit.symbol}")
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
        
        # Inicjalizacja loggera
        logger = logging.getLogger(__name__)
        logger.info(f"Używanie składników do przepisu: {recipe.title}")
        
        # Jeśli nie podano liczby porcji, użyj domyślnej z przepisu
        if not servings:
            servings = recipe.servings
            
        # Oblicz współczynnik skalowania
        scale_factor = float(servings) / float(recipe.servings)
        logger.info(f"Współczynnik skalowania: {scale_factor} (z {recipe.servings} na {servings} porcji)")
        
        # Import funkcji konwersji jednostek
        from recipes.utils import convert_units
        
        # Sprawdź, czy wszystkie składniki są dostępne w wystarczającej ilości
        for ingredient_entry in recipe.ingredients.all():
            ingredient = ingredient_entry.ingredient
            amount_needed = float(ingredient_entry.amount) * scale_factor
            unit = ingredient_entry.unit
            
            logger.info(f"Sprawdzam dostępność: {amount_needed} {unit.symbol} składnika {ingredient.name}")
            
            # Sprawdź dostępność składnika
            if not cls.check_ingredient_availability(user, ingredient, amount_needed, unit):
                result["success"] = False
                result["missing"].append({
                    "ingredient": ingredient,
                    "amount_needed": amount_needed,
                    "unit": unit
                })
                logger.warning(f"Brak wystarczającej ilości {ingredient.name} ({amount_needed} {unit.symbol})")
        
        # Jeśli wszystkie składniki są dostępne, usuń je z lodówki
        if result["success"]:
            for ingredient_entry in recipe.ingredients.all():
                ingredient = ingredient_entry.ingredient
                amount_needed = float(ingredient_entry.amount) * scale_factor
                unit = ingredient_entry.unit
                
                logger.info(f"Usuwam z lodówki: {amount_needed} {unit.symbol} składnika {ingredient.name}")
                
                # Pobierz dostępne w lodówce produkty dla tego składnika, posortowane po dacie ważności (FIFO)
                fridge_items = cls.objects.filter(
                    user=user,
                    ingredient=ingredient
                ).order_by('expiry_date', 'purchase_date')  # najpierw najkrótszy termin ważności, potem najstarsze zakupy
                
                amount_to_remove = amount_needed
                removed_items = []
                
                # Najpierw użyj produktów w tej samej jednostce, co w przepisie
                for item in fridge_items.filter(unit=unit):
                    # Jeśli już usunęliśmy całą potrzebną ilość, przerwij pętlę
                    if amount_to_remove <= 0:
                        break
                    
                    try:
                        # Zapewnij, że wartości są typu float
                        item_amount = float(item.amount)
                        
                        if item_amount > amount_to_remove:
                            # Mamy wystarczającą ilość w tym produkcie
                            item.amount = item_amount - amount_to_remove
                            item.save()
                            
                            # Rejestruj użycie - ile i z jakiego produktu
                            removed_items.append({
                                'item': item,
                                'amount': amount_to_remove,
                                'unit': item.unit
                            })
                            
                            logger.info(f"Użyto {amount_to_remove} {unit.symbol} z {item}")
                            
                            # Zaktualizuj ilość do usunięcia na 0
                            amount_to_remove = 0
                        else:
                            # Zużywamy cały produkt
                            removed_items.append({
                                'item': item,
                                'amount': item_amount,
                                'unit': item.unit,
                                'fully_used': True
                            })
                            
                            logger.info(f"Użyto całego produktu: {item}")
                            
                            # Odejmij usuniętą ilość od ilości do usunięcia
                            amount_to_remove -= item_amount
                            
                            # Usuń produkt z lodówki
                            item.delete()
                    except Exception as e:
                        logger.error(f"Błąd podczas usuwania składnika {ingredient.name}: {e}")
                        continue
                
                # Jeśli nadal potrzebujemy więcej, użyj produktów w innych jednostkach
                if amount_to_remove > 0:
                    logger.info(f"Potrzeba jeszcze {amount_to_remove} {unit.symbol} składnika {ingredient.name}")
                    
                    for item in fridge_items.exclude(unit=unit):
                        # Jeśli już usunęliśmy całą potrzebną ilość, przerwij pętlę
                        if amount_to_remove <= 0:
                            break
                        
                        try:
                            # Konwertuj ilość potrzebną na jednostkę produktu w lodówce
                            converted_amount = convert_units(amount_to_remove, unit, item.unit, ingredient=ingredient)
                            
                            # Zapewnij, że wartości są typu float
                            item_amount = float(item.amount)
                            converted_amount = float(converted_amount)
                            
                            logger.info(f"Konwersja: {amount_to_remove} {unit.symbol} = {converted_amount} {item.unit.symbol}")
                                
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
                                
                                # Konwersja z powrotem na jednostkę przepisu, aby odliczyć od amount_to_remove
                                amount_removed_in_recipe_unit = convert_units(converted_amount, item.unit, unit, ingredient=ingredient)
                                
                                logger.info(f"Użyto {converted_amount} {item.unit.symbol} z {item} (odpowiada {amount_removed_in_recipe_unit} {unit.symbol})")
                                
                                # Zaktualizuj ilość do usunięcia
                                amount_to_remove -= amount_removed_in_recipe_unit
                            else:
                                # Zużywamy cały produkt
                                # Konwertuj ilość z produktu na jednostkę przepisu
                                amount_removed_in_recipe_unit = convert_units(item_amount, item.unit, unit, ingredient=ingredient)
                                
                                removed_items.append({
                                    'item': item,
                                    'amount': item_amount,
                                    'unit': item.unit,
                                    'fully_used': True,
                                    'equivalent': amount_removed_in_recipe_unit
                                })
                                
                                logger.info(f"Użyto całego produktu: {item} (odpowiada {amount_removed_in_recipe_unit} {unit.symbol})")
                                
                                # Odejmij usuniętą ilość od ilości do usunięcia (w jednostkach przepisu)
                                amount_to_remove -= amount_removed_in_recipe_unit
                                
                                # Usuń produkt z lodówki
                                item.delete()
                        except Exception as e:
                            logger.error(f"Błąd podczas usuwania składnika {ingredient.name} (konwersja): {e}")
                            continue
                
                # Dodaj informację o zużytym składniku do wyniku
                result["used"].append({
                    "ingredient": ingredient,
                    "amount": ingredient_entry.amount * scale_factor,
                    "unit": unit,
                    "items_used": removed_items,
                    "remaining_amount": max(0, amount_to_remove)
                })
                
                if amount_to_remove > 0:
                    logger.warning(f"Nie udało się usunąć całej ilości {ingredient.name}. Pozostało {amount_to_remove} {unit.symbol}")
        
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
        
        try:
            amount = float(amount)
            if amount <= 0:
                # Jeśli nie potrzebujemy składnika, to jest dostępny
                return True
        except (ValueError, TypeError):
            # Błąd konwersji - nieprawidłowa wartość ilości
            return False
        
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
        logger = logging.getLogger(__name__)
        
        for item in items:
            try:
                # Jeśli jednostki są różne, przelicz ilość
                if item.unit != unit:
                    try:
                        from recipes.utils import convert_units
                        converted_amount = convert_units(float(item.amount), item.unit, unit, ingredient=ingredient)
                        logger.info(f"Konwersja dla {ingredient.name}: {item.amount} {item.unit.symbol} = {converted_amount} {unit.symbol}")
                        total_available += converted_amount
                    except (ValueError, TypeError) as e:
                        # Logowanie błędu dla debugowania
                        logger.error(f"Błąd konwersji: {e} dla {item.ingredient.name} z {item.unit.symbol} na {unit.symbol}")
                        # Ignoruj ten produkt, jeśli konwersja nie jest możliwa
                        continue
                else:
                    total_available += float(item.amount)
            except Exception as e:
                # W przypadku nieoczekiwanego błędu, ignoruj ten produkt
                logger.error(f"Nieoczekiwany błąd: {e}")
                continue
        
        # Dodajemy logi do debugowania
        logger.info(f"Sprawdzanie dostępności {ingredient.name}: potrzeba {amount} {unit.symbol}, dostępne {total_available} {unit.symbol}")
        
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


