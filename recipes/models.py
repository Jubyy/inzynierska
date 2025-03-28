from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

class IngredientCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nazwa kategorii")
    is_vegetarian = models.BooleanField(default=True, verbose_name="Wegetariański")
    is_vegan = models.BooleanField(default=False, verbose_name="Wegański")

    class Meta:
        verbose_name = "Kategoria składnika"
        verbose_name_plural = "Kategorie składników"

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nazwa składnika")
    category = models.ForeignKey(IngredientCategory, on_delete=models.CASCADE, related_name='ingredients', verbose_name="Kategoria")
    description = models.TextField(blank=True, null=True, verbose_name="Opis")
    
    class Meta:
        verbose_name = "Składnik"
        verbose_name_plural = "Składniki"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    @property
    def is_vegetarian(self):
        return self.category.is_vegetarian
    
    @property
    def is_vegan(self):
        return self.category.is_vegan

class MeasurementUnit(models.Model):
    name = models.CharField(max_length=50, verbose_name="Nazwa jednostki")
    symbol = models.CharField(max_length=10, verbose_name="Symbol")
    is_base = models.BooleanField(default=False, verbose_name="Jednostka bazowa")
    
    class Meta:
        verbose_name = "Jednostka miary"
        verbose_name_plural = "Jednostki miary"

    def __str__(self):
        return f"{self.name} ({self.symbol})"

class UnitConversion(models.Model):
    from_unit = models.ForeignKey(MeasurementUnit, related_name='conversions_from', on_delete=models.CASCADE, verbose_name="Z jednostki")
    to_unit = models.ForeignKey(MeasurementUnit, related_name='conversions_to', on_delete=models.CASCADE, verbose_name="Na jednostkę")
    ratio = models.FloatField(verbose_name="Współczynnik konwersji")
    
    class Meta:
        verbose_name = "Konwersja jednostek"
        verbose_name_plural = "Konwersje jednostek"
        unique_together = ('from_unit', 'to_unit')

    def __str__(self):
        return f"{self.from_unit.symbol} → {self.to_unit.symbol} (× {self.ratio})"

class RecipeCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nazwa kategorii")
    description = models.TextField(blank=True, null=True, verbose_name="Opis")
    
    class Meta:
        verbose_name = "Kategoria przepisu"
        verbose_name_plural = "Kategorie przepisów"

    def __str__(self):
        return self.name

class Recipe(models.Model):
    title = models.CharField(max_length=200, verbose_name="Tytuł")
    description = models.TextField(verbose_name="Opis")
    instructions = models.TextField(verbose_name="Instrukcje przygotowania")
    servings = models.PositiveIntegerField(default=4, verbose_name="Liczba porcji")
    preparation_time = models.PositiveIntegerField(help_text="Czas przygotowania w minutach", verbose_name="Czas przygotowania")
    image = models.ImageField(upload_to='recipes/', blank=True, null=True, verbose_name="Zdjęcie")
    categories = models.ManyToManyField(RecipeCategory, related_name='recipes', verbose_name="Kategorie")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Autor")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data aktualizacji")
    
    class Meta:
        verbose_name = "Przepis"
        verbose_name_plural = "Przepisy"
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('recipes:detail', args=[str(self.id)])
    
    @property
    def is_vegetarian(self):
        return all(ing.ingredient.is_vegetarian for ing in self.ingredients.all())
    
    @property
    def is_vegan(self):
        return all(ing.ingredient.is_vegan for ing in self.ingredients.all())
    
    def get_missing_ingredients(self, user):
        from fridge.models import FridgeItem
        from recipes.utils import convert_units
        
        missing = []
        for recipe_ing in self.ingredients.all():
            # Sprawdź, czy składnik jest w lodówce i w wystarczającej ilości
            fridge_items = FridgeItem.objects.filter(
                user=user, 
                ingredient=recipe_ing.ingredient
            )
            
            total_available = 0
            for item in fridge_items:
                # Konwersja jednostek jeśli potrzebna
                if item.unit == recipe_ing.unit:
                    total_available += item.amount
                else:
                    try:
                        converted_amount = convert_units(item.amount, item.unit, recipe_ing.unit)
                        total_available += converted_amount
                    except ValueError:
                        # Jeśli konwersja niemożliwa, ignoruj ten składnik
                        pass
            
            if total_available < recipe_ing.amount:
                missing.append({
                    'ingredient': recipe_ing.ingredient,
                    'required': recipe_ing.amount,
                    'available': total_available,
                    'missing': recipe_ing.amount - total_available,
                    'unit': recipe_ing.unit
                })
        
        return missing
    
    def can_be_prepared_with_available_ingredients(self, user):
        missing_ingredients = self.get_missing_ingredients(user)
        return len(missing_ingredients) == 0
    
    def scale_to_servings(self, target_servings):
        """Zwraca składniki przepisu przeskalowane do podanej liczby porcji"""
        if target_servings <= 0 or self.servings <= 0:
            raise ValueError("Liczba porcji musi być większa od zera")
        
        scale_factor = target_servings / self.servings
        scaled_ingredients = []
        
        for ingredient in self.ingredients.all():
            scaled_amount = ingredient.amount * scale_factor
            scaled_ingredients.append({
                'ingredient': ingredient.ingredient,
                'amount': scaled_amount,
                'unit': ingredient.unit
            })
            
        return scaled_ingredients

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='ingredients', on_delete=models.CASCADE, verbose_name="Przepis")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, verbose_name="Składnik")
    amount = models.FloatField(verbose_name="Ilość")
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.SET_NULL, null=True, verbose_name="Jednostka")
    
    class Meta:
        verbose_name = "Składnik przepisu"
        verbose_name_plural = "Składniki przepisu"
        unique_together = ('recipe', 'ingredient')

    def __str__(self):
        return f"{self.amount} {self.unit.symbol if self.unit else ''} {self.ingredient.name}" 