from django.db import models
from django.contrib.auth.models import User
from recipes.models import Ingredient, MeasurementUnit, Recipe
from django.utils import timezone

class ShoppingList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_lists', verbose_name="Użytkownik")
    name = models.CharField(max_length=100, verbose_name="Nazwa listy")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    modified_at = models.DateTimeField(auto_now=True, verbose_name="Data modyfikacji")
    is_completed = models.BooleanField(default=False, verbose_name="Zakończona")
    recipe = models.ForeignKey('recipes.Recipe', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Przepis źródłowy")
    
    class Meta:
        verbose_name = "Lista zakupów"
        verbose_name_plural = "Listy zakupów"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    @property
    def item_count(self):
        """Zwraca liczbę pozycji na liście zakupów"""
        return self.items.count()
    
    @property
    def completed_item_count(self):
        """Zwraca liczbę zakupionych pozycji na liście"""
        return self.items.filter(is_purchased=True).count()
    
    @property
    def progress_percentage(self):
        """Zwraca procent ukończenia listy zakupów"""
        if self.item_count == 0:
            return 0
        return int((self.completed_item_count / self.item_count) * 100)
    
    def normalize_units(self):
        """
        Konsoliduje produkty na liście zakupów, łącząc te same składniki
        i konwertując je do jednostek podstawowych.
        
        Returns:
            int: Liczba skonsolidowanych produktów
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
        
        # Pobierz wszystkie składniki z listy zakupów
        ingredients_groups = self.items.values('ingredient_id').distinct()
        consolidated_count = 0
        
        # Dla każdego unikalnego składnika
        for ing_data in ingredients_groups:
            ingredient_id = ing_data['ingredient_id']
            
            # Pobierz wszystkie wpisy dla tego składnika
            items = self.items.filter(
                ingredient_id=ingredient_id
            ).select_related('ingredient', 'unit')
            
            if not items or items.count() <= 1:
                continue
                
            # Określ podstawową jednostkę dla tego składnika
            first_item = items[0]
            ingredient = first_item.ingredient
            unit_type = 'weight'  # domyślnie zakładamy wagę
            
            if ingredient.unit_type.startswith('volume'):
                unit_type = 'volume'
                base_unit = ml_unit
            else:
                base_unit = gram_unit
            
            # Przygotuj się do konsolidacji zakupionych i niezakupionych osobno
            for is_purchased in [False, True]:
                purchase_items = items.filter(is_purchased=is_purchased)
                
                if purchase_items.count() <= 1:
                    continue
                
                # Skonsoliduj do jednego wpisu
                total_amount = 0
                for item in purchase_items:
                    try:
                        # Konwertuj do jednostki podstawowej i dodaj
                        if item.unit != base_unit:
                            # Próbuj dokonać konwersji
                            try:
                                converted = convert_units(item.amount, item.unit, base_unit, ingredient=ingredient)
                                total_amount += converted
                            except Exception as e:
                                print(f"Błąd konwersji dla {item.ingredient.name}: {str(e)}")
                                # Jeśli konwersja się nie powiedzie, zachowaj ten element
                                continue
                        else:
                            total_amount += item.amount
                    except Exception as e:
                        print(f"Błąd podczas konsolidacji {item.ingredient.name}: {str(e)}")
                        continue
                
                # Usuń skonsolidowane elementy
                items_to_delete = list(purchase_items)
                first_item = items_to_delete.pop(0)  # zachowaj pierwszy element, aby zaktualizować go
                
                # Usuń pozostałe elementy
                ShoppingItem.objects.filter(id__in=[item.id for item in items_to_delete]).delete()
                
                # Zaktualizuj pierwszy element o nową ilość i jednostkę
                first_item.amount = total_amount
                first_item.unit = base_unit
                first_item.save()
                
                consolidated_count += len(items_to_delete)  # liczba usuniętych elementów
        
        return consolidated_count
    
    def add_recipe_ingredients(self, recipe, servings=None):
        """
        Dodaje składniki z przepisu do listy zakupów.
        
        Args:
            recipe (Recipe): Przepis
            servings (int, optional): Liczba porcji. Domyślnie używa liczby porcji z przepisu.
            
        Returns:
            list: Lista utworzonych pozycji
        """
        # Jeśli nie podano liczby porcji, użyj domyślnej z przepisu
        if not servings:
            servings = recipe.servings
            
        # Oblicz współczynnik skalowania
        scale_factor = servings / recipe.servings
        created_items = []
        
        for ingredient_entry in recipe.ingredients.all():
            ingredient = ingredient_entry.ingredient
            amount = ingredient_entry.amount * scale_factor
            unit = ingredient_entry.unit
            
            # Sprawdź, czy ten składnik już jest na liście
            existing_item = self.items.filter(ingredient=ingredient, unit=unit).first()
            
            if existing_item:
                # Jeśli tak, zwiększ ilość
                existing_item.amount += amount
                existing_item.save()
                created_items.append(existing_item)
            else:
                # Jeśli nie, utwórz nową pozycję
                item = ShoppingItem.objects.create(
                    shopping_list=self,
                    ingredient=ingredient,
                    amount=amount,
                    unit=unit,
                    recipe=recipe
                )
                created_items.append(item)
                
        return created_items
    
    def add_missing_ingredients(self, recipe, servings=None):
        """
        Dodaje do listy zakupów brakujące składniki do przygotowania przepisu.
        
        Args:
            recipe (Recipe): Przepis
            servings (int, optional): Liczba porcji. Domyślnie używa liczby porcji z przepisu.
            
        Returns:
            list: Lista utworzonych obiektów ShoppingItem
        """
        # Pobierz brakujące składniki z przepisu
        missing_ingredients = recipe.get_missing_ingredients(self.user, servings)
        print(f"DEBUG: Znaleziono {len(missing_ingredients)} brakujących składników")
        
        if not missing_ingredients:
            print("DEBUG: Brak brakujących składników, zwracam pustą listę")
            return []
            
        created_items = []
        
        # Oblicz współczynnik skalowania, jeśli podano liczbę porcji inną niż domyślna
        scale_factor = 1.0
        if servings and servings != recipe.servings:
            scale_factor = float(servings) / float(recipe.servings)
            print(f"DEBUG: Współczynnik skalowania: {scale_factor}")
            
        # Przetwarzaj każdy brakujący składnik
        for ingredient_entry in missing_ingredients:
            # Pobierz informacje o składniku
            ingredient = ingredient_entry.ingredient
            amount = float(ingredient_entry.missing)  # Używamy już przeskalowanej wartości brakującej ilości
            unit = ingredient_entry.unit
            
            print(f"DEBUG: Dodaję składnik: {ingredient.name}, {amount} {unit.symbol}")
            
            # Sprawdź, czy ten składnik już jest na liście
            existing_item = self.items.filter(ingredient=ingredient, unit=unit).first()
            
            if existing_item:
                # Jeśli tak, zwiększ ilość
                print(f"DEBUG: Składnik już istnieje na liście, aktualizuję ilość")
                existing_item.amount = max(existing_item.amount, amount)  # Ustaw większą wartość
                existing_item.save()
                created_items.append(existing_item)
            else:
                # Jeśli nie, utwórz nową pozycję
                print(f"DEBUG: Tworzę nowy składnik na liście")
                item = ShoppingItem.objects.create(
                    shopping_list=self,
                    ingredient=ingredient,
                    amount=amount,
                    unit=unit,
                    recipe=recipe
                )
                created_items.append(item)
                print(f"DEBUG: Utworzono składnik, ID: {item.id}")
                
        print(f"DEBUG: Dodano {len(created_items)} składników do listy zakupów")
        return created_items
    
    def complete_shopping(self):
        """
        Oznacza wszystkie pozycje jako zakupione i dodaje je do lodówki.
        
        Returns:
            int: Liczba pozycji dodanych do lodówki
        """
        from fridge.models import FridgeItem
        
        added_count = 0
        
        for item in self.items.filter(is_purchased=False):
            # Dodaj do lodówki
            FridgeItem.add_to_fridge(
                user=self.user,
                ingredient=item.ingredient,
                amount=item.amount,
                unit=item.unit
            )
            
            # Oznacz jako zakupione
            item.is_purchased = True
            item.purchase_date = timezone.now()
            item.save()
            
            added_count += 1
            
        # Oznacz listę jako zakończoną
        self.is_completed = True
        self.save()
        
        return added_count

    def get_items_by_category(self):
        """
        Grupuje pozycje na liście zakupów według kategorii.
        
        Returns:
            dict: Słownik z kategoriami jako kluczami i listami pozycji jako wartościami
        """
        result = {}
        
        # Pobierz wszystkie pozycje na liście
        items = self.items.select_related('ingredient', 'ingredient__category', 'unit')
        
        # Grupuj według kategorii
        for item in items:
            category_name = item.ingredient.category.name if item.ingredient.category else "Bez kategorii"
            
            if category_name not in result:
                result[category_name] = []
            
            result[category_name].append(item)
        
        # Sortuj kategorie
        sorted_result = {}
        for category in sorted(result.keys()):
            sorted_result[category] = sorted(result[category], key=lambda x: x.ingredient.name)
        
        return sorted_result

    def get_unpurchased_items_by_category(self):
        """
        Grupuje niezakupione pozycje na liście zakupów według kategorii.
        
        Returns:
            dict: Słownik z kategoriami jako kluczami i listami niezakupionych pozycji jako wartościami
        """
        result = {}
        
        # Pobierz niezakupione pozycje
        items = self.items.filter(is_purchased=False).select_related('ingredient', 'ingredient__category', 'unit')
        
        # Grupuj według kategorii
        for item in items:
            category_name = item.ingredient.category.name if item.ingredient.category else "Bez kategorii"
            
            if category_name not in result:
                result[category_name] = []
            
            result[category_name].append(item)
        
        # Sortuj kategorie
        sorted_result = {}
        for category in sorted(result.keys()):
            sorted_result[category] = sorted(result[category], key=lambda x: x.ingredient.name)
        
        return sorted_result

    def get_purchased_items_by_category(self):
        """
        Grupuje zakupione pozycje na liście zakupów według kategorii.
        
        Returns:
            dict: Słownik z kategoriami jako kluczami i listami zakupionych pozycji jako wartościami
        """
        result = {}
        
        # Pobierz zakupione pozycje
        items = self.items.filter(is_purchased=True).select_related('ingredient', 'ingredient__category', 'unit')
        
        # Grupuj według kategorii
        for item in items:
            category_name = item.ingredient.category.name if item.ingredient.category else "Bez kategorii"
            
            if category_name not in result:
                result[category_name] = []
            
            result[category_name].append(item)
        
        # Sortuj kategorie
        sorted_result = {}
        for category in sorted(result.keys()):
            sorted_result[category] = sorted(result[category], key=lambda x: x.ingredient.name)
        
        return sorted_result

class ShoppingItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items', verbose_name="Lista zakupów")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, verbose_name="Składnik")
    amount = models.FloatField(verbose_name="Ilość")
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, verbose_name="Jednostka")
    is_purchased = models.BooleanField(default=False, verbose_name="Zakupione")
    purchase_date = models.DateTimeField(null=True, blank=True, verbose_name="Data zakupu")
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Przepis")
    note = models.CharField(max_length=200, blank=True, verbose_name="Notatka")
    
    class Meta:
        verbose_name = "Pozycja na liście zakupów"
        verbose_name_plural = "Pozycje na liście zakupów"
        ordering = ['ingredient__name']
    
    def __str__(self):
        return f"{self.amount} {self.unit.symbol} {self.ingredient.name}"
    
    def mark_as_purchased(self):
        """
        Oznacza produkt jako zakupiony i dodaje go do lodówki.
        
        Returns:
            bool: True jeśli udało się dodać do lodówki, False w przeciwnym razie
        """
        from django.utils import timezone
        from fridge.models import FridgeItem
        
        # Oznacz jako zakupiony
        self.is_purchased = True
        self.purchase_date = timezone.now()
        self.save()
        
        # Dodaj do lodówki, jeśli nie jest już zakupiony
        try:
            FridgeItem.add_to_fridge(
                user=self.shopping_list.user,
                ingredient=self.ingredient,
                amount=self.amount,
                unit=self.unit
            )
            return True
        except Exception as e:
            print(f"Błąd podczas dodawania do lodówki: {str(e)}")
            return False
