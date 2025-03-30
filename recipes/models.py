from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    barcode = models.CharField(max_length=30, blank=True, null=True, verbose_name="Kod kreskowy", unique=True)
    default_unit = models.ForeignKey('MeasurementUnit', on_delete=models.SET_NULL, null=True, blank=True, related_name='default_for_ingredients', verbose_name="Domyślna jednostka")
    compatible_units = models.ManyToManyField('MeasurementUnit', blank=True, related_name='compatible_ingredients', verbose_name="Kompatybilne jednostki")
    
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

    def save(self, *args, **kwargs):
        """Zapisz model i dodaj domyślną jednostkę do kompatybilnych"""
        super().save(*args, **kwargs)
        
        # Dodaj domyślną jednostkę do kompatybilnych, jeśli istnieje
        if self.default_unit and not self.compatible_units.filter(id=self.default_unit.id).exists():
            self.compatible_units.add(self.default_unit)

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
    is_public = models.BooleanField(default=True, verbose_name="Publiczny")
    
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
    
    @property
    def is_meat(self):
        """Zwraca True, jeśli przepis nie jest wegetariański (zawiera mięso)"""
        return not self.is_vegetarian
    
    @property
    def likes_count(self):
        """Zwraca liczbę polubień przepisu"""
        return self.likes.count()
    
    @property
    def comments_count(self):
        """Zwraca liczbę komentarzy do przepisu (tylko komentarze główne, bez odpowiedzi)"""
        return self.comments.filter(parent=None).count()
    
    def is_liked_by(self, user):
        """Sprawdza, czy przepis jest polubiony przez danego użytkownika"""
        if not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()
    
    def toggle_like(self, user):
        """Przełącza polubienie przepisu przez użytkownika (dodaje/usuwa)"""
        if not user.is_authenticated:
            return False
        
        like = self.likes.filter(user=user).first()
        if like:
            like.delete()
            return False
        else:
            RecipeLike.objects.create(user=user, recipe=self)
            return True
    
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

class FavoriteRecipe(models.Model):
    """Model do przechowywania ulubionych przepisów użytkownika"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_recipes', verbose_name="Użytkownik")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorited_by', verbose_name="Przepis")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    
    class Meta:
        verbose_name = "Ulubiony przepis"
        verbose_name_plural = "Ulubione przepisy"
        unique_together = ('user', 'recipe')  # Użytkownik może dodać przepis do ulubionych tylko raz
        
    def __str__(self):
        return f"{self.user.username} - {self.recipe.title}"

class RecipeLike(models.Model):
    """Model do przechowywania polubień (łapek w górę) dla przepisów"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_likes', verbose_name="Użytkownik")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='likes', verbose_name="Przepis")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    
    class Meta:
        verbose_name = "Polubienie przepisu"
        verbose_name_plural = "Polubienia przepisów"
        unique_together = ('user', 'recipe')  # Użytkownik może polubić przepis tylko raz
        
    def __str__(self):
        return f"{self.user.username} polubił {self.recipe.title}"

class Comment(models.Model):
    """Model do przechowywania komentarzy do przepisów"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_comments', verbose_name="Autor")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='comments', verbose_name="Przepis")
    content = models.TextField(verbose_name="Treść komentarza")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data aktualizacji")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies', verbose_name="Komentarz nadrzędny")
    
    class Meta:
        verbose_name = "Komentarz"
        verbose_name_plural = "Komentarze"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Komentarz od {self.user.username} do {self.recipe.title}"
    
    @property
    def is_reply(self):
        """Sprawdza, czy komentarz jest odpowiedzią na inny komentarz"""
        return self.parent is not None

class MealPlan(models.Model):
    """Model do przechowywania planów posiłków"""
    MEAL_TYPES = [
        ('breakfast', 'Śniadanie'),
        ('lunch', 'Drugie śniadanie'),
        ('dinner', 'Obiad'),
        ('snack', 'Przekąska'),
        ('supper', 'Kolacja'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_plans', verbose_name="Użytkownik")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='meal_plans', verbose_name="Przepis", null=True, blank=True)
    date = models.DateField(verbose_name="Data")
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES, verbose_name="Rodzaj posiłku")
    servings = models.PositiveIntegerField(default=1, verbose_name="Liczba porcji")
    notes = models.TextField(blank=True, null=True, verbose_name="Notatki")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    completed = models.BooleanField(default=False, verbose_name="Zrealizowano")
    custom_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Własna nazwa posiłku")
    
    class Meta:
        verbose_name = "Plan posiłku"
        verbose_name_plural = "Plany posiłków"
        ordering = ['date', 'meal_type']
        # Już nie potrzebujemy recipe w unique_together, bo teraz może być null
        unique_together = ('user', 'date', 'meal_type')
        
    def __str__(self):
        meal_name = self.custom_name if self.custom_name else (self.recipe.title if self.recipe else "Własny posiłek")
        return f"{self.get_meal_type_display()} - {meal_name} ({self.date})"
    
    def get_ingredients_for_shopping(self):
        """Zwraca składniki potrzebne do przygotowania posiłku, dostosowane do liczby porcji"""
        if self.recipe:
            return self.recipe.scale_to_servings(self.servings)
        return []
        
    @property
    def meal_name(self):
        """Zwraca nazwę posiłku - własną lub z przepisu"""
        return self.custom_name if self.custom_name else (self.recipe.title if self.recipe else "Własny posiłek") 