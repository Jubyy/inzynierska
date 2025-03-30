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
            dict: Słownik z informacjami o dodanych składnikach
        """
        from fridge.models import FridgeItem
        
        missing_ingredients = recipe.get_missing_ingredients(self.user)
        created_items = []
        
        for missing in missing_ingredients:
            ingredient = missing['ingredient']
            amount = missing['missing']
            unit = missing['unit']
            
            # Sprawdź, czy ten składnik już jest na liście
            existing_item = self.items.filter(ingredient=ingredient, unit=unit).first()
            
            if existing_item:
                # Jeśli tak, zwiększ ilość ale tylko jeśli nowa ilość jest większa
                if amount > existing_item.amount:
                    existing_item.amount = amount
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

    def add_ingredient(self, ingredient, amount, unit):
        """
        Dodaje składnik do listy zakupów.
        
        Args:
            ingredient (Ingredient): Składnik
            amount (float): Ilość
            unit (MeasurementUnit): Jednostka
            
        Returns:
            ShoppingItem: Utworzona lub zaktualizowana pozycja
        """
        # Sprawdź, czy ten składnik już jest na liście
        existing_item = self.items.filter(ingredient=ingredient, unit=unit).first()
        
        if existing_item:
            # Jeśli tak, zwiększ ilość
            existing_item.amount += amount
            existing_item.save()
            return existing_item
        else:
            # Jeśli nie, utwórz nową pozycję
            item = ShoppingItem.objects.create(
                shopping_list=self,
                ingredient=ingredient,
                amount=amount,
                unit=unit
            )
            return item
            
    def optimize(self):
        """
        Optymalizuje listę zakupów, łącząc podobne składniki.
        
        Returns:
            int: Liczba zoptymalizowanych pozycji
        """
        from recipes.utils import convert_units
        
        # Grupuj składniki według ID
        ingredient_groups = {}
        
        # Zbierz wszystkie pozycje według składnika
        for item in self.items.all():
            if item.ingredient.id not in ingredient_groups:
                ingredient_groups[item.ingredient.id] = []
            ingredient_groups[item.ingredient.id].append(item)
        
        optimized_count = 0
        
        # Dla każdej grupy składników
        for ingredient_id, items in ingredient_groups.items():
            if len(items) <= 1:
                continue  # Nie ma co optymalizować, jeśli jest tylko jeden element
            
            # Wybierz jednostkę, która najczęściej występuje
            unit_count = {}
            for item in items:
                unit_id = item.unit.id
                if unit_id not in unit_count:
                    unit_count[unit_id] = 0
                unit_count[unit_id] += 1
            
            # Sortuj według częstotliwości występowania (od najwyższej)
            most_common_unit_id = sorted(unit_count.items(), key=lambda x: x[1], reverse=True)[0][0]
            most_common_unit = items[0].unit.__class__.objects.get(id=most_common_unit_id)
            
            # Zbierz całkowitą ilość, konwertując jednostki
            total_amount = 0
            for item in items:
                if item.unit.id == most_common_unit_id:
                    total_amount += item.amount
                else:
                    try:
                        # Spróbuj przekonwertować jednostkę
                        converted_amount = convert_units(item.amount, item.unit, most_common_unit)
                        if converted_amount is not None:
                            total_amount += converted_amount
                    except:
                        # Jeśli konwersja się nie powiedzie, zachowaj oryginalną pozycję
                        pass
            
            # Usuń wszystkie stare pozycje
            for item in items:
                item.delete()
            
            # Utwórz nową, zoptymalizowaną pozycję
            ShoppingItem.objects.create(
                shopping_list=self,
                ingredient=items[0].ingredient,
                amount=total_amount,
                unit=most_common_unit
            )
            
            optimized_count += 1
        
        return optimized_count

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
        """Oznacza pozycję jako zakupioną i dodaje do lodówki"""
        from fridge.models import FridgeItem
        
        if not self.is_purchased:
            # Dodaj do lodówki
            FridgeItem.add_to_fridge(
                user=self.shopping_list.user,
                ingredient=self.ingredient,
                amount=self.amount,
                unit=self.unit
            )
            
            # Oznacz jako zakupione
            self.is_purchased = True
            self.purchase_date = timezone.now()
            self.save()
            
            # Sprawdź, czy wszystkie pozycje na liście są zakupione
            all_purchased = not self.shopping_list.items.filter(is_purchased=False).exists()
            
            if all_purchased:
                # Oznacz listę jako zakończoną
                self.shopping_list.is_completed = True
                self.shopping_list.save()
