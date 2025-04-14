from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import datetime

class IngredientCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nazwa kategorii")
    is_vegetarian = models.BooleanField(default=True, verbose_name="Wegetariański")
    is_vegan = models.BooleanField(default=False, verbose_name="Wegański")

    class Meta:
        verbose_name = "Kategoria składnika"
        verbose_name_plural = "Kategorie składników"
        ordering = ['name']

    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        """Automatycznie ustawia flagi wegetariańskie i wegańskie na podstawie nazwy kategorii"""
        # Najpierw zapisz model, żeby zapewnić, że ma on ID
        super().save(*args, **kwargs)
        
        # Lista kategorii niewegetariańskich
        non_vegetarian_categories = ['mięso', 'mieso', 'wędliny', 'wedliny', 'ryby', 'owoce morza', 'drób', 'drob']
        # Lista kategorii wegańskich
        vegan_categories = ['warzywa', 'owoce', 'nasiona', 'ziarna', 'strączkowe', 'strączkowe', 'przyprawy', 'zioła', 'ziola']
        # Lista kategorii wegetariańskich, ale nie wegańskich
        vegetarian_not_vegan = ['nabiał', 'nabial', 'jaja', 'jajka', 'miód', 'miod']
        
        name_lower = self.name.lower()
        
        # Ustaw is_vegetarian na False dla niewegetariańskich kategorii
        if any(category in name_lower for category in non_vegetarian_categories):
            self.is_vegetarian = False
            self.is_vegan = False
            super().save(update_fields=['is_vegetarian', 'is_vegan'])
        # Ustaw is_vegan na True dla wegańskich kategorii
        elif any(category in name_lower for category in vegan_categories):
            self.is_vegetarian = True
            self.is_vegan = True
            super().save(update_fields=['is_vegetarian', 'is_vegan'])
        # Dla kategorii wegetariańskich, ale nie wegańskich
        elif any(category in name_lower for category in vegetarian_not_vegan):
            self.is_vegetarian = True
            self.is_vegan = False
            super().save(update_fields=['is_vegetarian', 'is_vegan'])

class MeasurementUnit(models.Model):
    name = models.CharField(max_length=50, verbose_name="Nazwa")
    symbol = models.CharField(max_length=10, verbose_name="Symbol")
    type = models.CharField(
        max_length=20,
        choices=[
            ('weight', 'Waga'),
            ('volume', 'Objętość'),
            ('piece', 'Sztuki'),
            ('spoon', 'Łyżki'),
            ('custom', 'Inne')
        ],
        default='weight',
        verbose_name="Typ jednostki"
    )
    base_ratio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('1.0000'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name="Przelicznik bazowy (w gramach lub mililitrach)"
    )
    is_common = models.BooleanField(default=False, verbose_name="Popularna miara kuchenna")
    description = models.CharField(max_length=200, blank=True, verbose_name="Opis/przykład")

    class Meta:
        verbose_name = "Jednostka miary"
        verbose_name_plural = "Jednostki miary"
        ordering = ['type', 'name']

    def __str__(self):
        return self.name

    def get_base_equivalent(self, amount):
        """Zwraca wartość w jednostce bazowej (gramy lub mililitry)"""
        return amount * self.base_ratio

    def get_display_equivalent(self, amount):
        """Zwraca sformatowany tekst z przeliczeniem na jednostkę bazową"""
        base_amount = self.get_base_equivalent(amount)
        if self.type in ['weight', 'spoon']:
            return f"{amount} {self.name} ({base_amount}g)"
        elif self.type == 'volume':
            return f"{amount} {self.name} ({base_amount}ml)"
        return f"{amount} {self.name}"
        
    @classmethod
    def get_common_units_by_type(cls, unit_type):
        """Zwraca popularne jednostki dla danego typu"""
        return cls.objects.filter(type=unit_type, is_common=True)
        
    @classmethod
    def get_units_for_ingredient_category(cls, category_name):
        """
        Zwraca odpowiednie jednostki miary dla danej kategorii składników
        """
        if category_name.lower() in ['mięso', 'wędliny']:
            # Dla mięsa, tylko jednostki wagi (głównie gramy i kilogramy)
            return cls.objects.filter(type='weight')
        elif category_name.lower() in ['nabiał']:
            # Dla nabiału, jednostki wagi i objętości
            return cls.objects.filter(type__in=['weight', 'volume'])
        elif category_name.lower() in ['warzywa', 'owoce']:
            # Dla warzyw i owoców, jednostki wagi i sztuki
            return cls.objects.filter(type__in=['weight', 'piece'])
        elif category_name.lower() in ['przyprawy']:
            # Dla przypraw, jednostki wagi i łyżki/łyżeczki
            return cls.objects.filter(type__in=['weight', 'spoon'])
        else:
            # Dla pozostałych, wszystkie jednostki
            return cls.objects.all()

class UnitConversion(models.Model):
    """Model reprezentujący konwersję między jednostkami miar"""
    from_unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, related_name='conversions_from')
    to_unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, related_name='conversions_to')
    ratio = models.DecimalField(max_digits=10, decimal_places=4)
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = [('from_unit', 'to_unit', 'ingredient')]
        verbose_name = "Konwersja jednostek"
        verbose_name_plural = "Konwersje jednostek"

    def __str__(self):
        return f"{self.from_unit} -> {self.to_unit} ({self.ratio})"

class Ingredient(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nazwa składnika")
    category = models.ForeignKey(IngredientCategory, on_delete=models.CASCADE, related_name='ingredients', verbose_name="Kategoria")
    description = models.TextField(blank=True, null=True, verbose_name="Opis")
    barcode = models.CharField(max_length=30, blank=True, null=True, verbose_name="Kod kreskowy", unique=True)
    default_unit = models.ForeignKey(MeasurementUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_for_ingredients', verbose_name="Domyślna jednostka")
    compatible_units = models.ManyToManyField(MeasurementUnit, blank=True, related_name='compatible_ingredients', verbose_name="Kompatybilne jednostki")
    density = models.DecimalField(
        max_digits=8, 
        decimal_places=3, 
        null=True, 
        blank=True,
        verbose_name="Gęstość [g/ml]",
        help_text="Gęstość w g/ml (dla konwersji między wagą a objętością)"
    )
    piece_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Waga sztuki [g]",
        help_text="Waga jednej sztuki w gramach"
    )
    unit_type = models.CharField(
        max_length=20,
        choices=[
            ('weight_only', 'Tylko waga (g, kg)'),
            ('volume_only', 'Tylko objętość (ml, l)'),
            ('piece_only', 'Tylko sztuki'),
            ('weight_volume', 'Waga i objętość'),
            ('weight_piece', 'Waga i sztuki'),
            ('weight_spoon', 'Waga i łyżki'),
            ('volume_spoon', 'Objętość i łyżki'),
            ('all', 'Wszystkie jednostki')
        ],
        default='weight_only',
        verbose_name="Dozwolone jednostki"
    )
    
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

    def get_allowed_units(self):
        """Zwraca queryset dozwolonych jednostek miary dla składnika"""
        if self.unit_type == 'weight_only':
            return MeasurementUnit.objects.filter(type='weight')
        elif self.unit_type == 'volume_only':
            return MeasurementUnit.objects.filter(type='volume')
        elif self.unit_type == 'piece_only':
            return MeasurementUnit.objects.filter(type='piece')
        elif self.unit_type == 'weight_volume':
            return MeasurementUnit.objects.filter(type__in=['weight', 'volume'])
        elif self.unit_type == 'weight_piece':
            return MeasurementUnit.objects.filter(type__in=['weight', 'piece'])
        elif self.unit_type == 'weight_spoon':
            return MeasurementUnit.objects.filter(type__in=['weight', 'spoon'])
        elif self.unit_type == 'volume_spoon':
            return MeasurementUnit.objects.filter(type__in=['volume', 'spoon'])
        else:  # all
            return MeasurementUnit.objects.all()

    def save(self, *args, **kwargs):
        """Zapisz model i dodaj domyślną jednostkę do kompatybilnych"""
        super().save(*args, **kwargs)
        
        # Dodaj domyślną jednostkę do kompatybilnych, jeśli istnieje
        if self.default_unit and not self.compatible_units.filter(id=self.default_unit.id).exists():
            self.compatible_units.add(self.default_unit)

    def convert_units(self, amount, from_unit, to_unit):
        """
        Konwertuje ilość z jednej jednostki na drugą
        """
        if from_unit == to_unit:
            return Decimal(str(amount))
            
        # Jeśli obie jednostki są tego samego typu (np. g -> kg)
        if from_unit.type == to_unit.type and from_unit.type != 'custom':
            base_amount = from_unit.convert_to_base(amount)
            return to_unit.convert_from_base(base_amount)
            
        # Konwersja między wagą a objętością
        if (from_unit.type == 'weight' and to_unit.type == 'volume') or \
           (from_unit.type == 'volume' and to_unit.type == 'weight'):
            if not self.density:
                raise ValueError(f"Brak zdefiniowanej gęstości dla {self.name}")
            
            if from_unit.type == 'weight':
                # Najpierw na gramy, potem na ml
                grams = from_unit.convert_to_base(amount)
                ml = grams / self.density
                return to_unit.convert_from_base(ml)
            else:
                # Najpierw na ml, potem na gramy
                ml = from_unit.convert_to_base(amount)
                grams = ml * self.density
                return to_unit.convert_from_base(grams)
                
        # Konwersja między sztukami a wagą
        if (from_unit.type == 'piece' and to_unit.type == 'weight') or \
           (from_unit.type == 'weight' and to_unit.type == 'piece'):
            if not self.piece_weight:
                raise ValueError(f"Brak zdefiniowanej wagi sztuki dla {self.name}")
            
            if from_unit.type == 'piece':
                grams = Decimal(str(amount)) * self.piece_weight
                return to_unit.convert_from_base(grams)
            else:
                grams = from_unit.convert_to_base(amount)
                return round(grams / self.piece_weight)
                
        # Sprawdź czy istnieje bezpośrednia konwersja
        try:
            conversion = UnitConversion.objects.get(
                ingredient=self,
                from_unit=from_unit,
                to_unit=to_unit
            )
            return conversion.convert(amount)
        except UnitConversion.DoesNotExist:
            # Spróbuj odwrotnej konwersji
            try:
                conversion = UnitConversion.objects.get(
                    ingredient=self,
                    from_unit=to_unit,
                    to_unit=from_unit
                )
                return Decimal(str(amount)) / conversion.ratio
            except UnitConversion.DoesNotExist:
                raise ValueError(f"Brak możliwości konwersji z {from_unit.symbol} na {to_unit.symbol} dla {self.name}")

class RecipeCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nazwa kategorii")
    description = models.TextField(blank=True, null=True, verbose_name="Opis")
    
    class Meta:
        verbose_name = "Kategoria przepisu"
        verbose_name_plural = "Kategorie przepisów"

    def __str__(self):
        return self.name

class Recipe(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Łatwy'),
        ('medium', 'Średni'),
        ('hard', 'Trudny'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Tytuł")
    description = models.TextField(verbose_name="Opis")
    instructions = models.TextField(verbose_name="Instrukcje przygotowania")
    servings = models.PositiveIntegerField(default=4, verbose_name="Liczba porcji")
    preparation_time = models.PositiveIntegerField(help_text="Czas przygotowania w minutach", verbose_name="Czas przygotowania")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium', verbose_name="Poziom trudności")
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
        """Zwraca liczbę komentarzy do przepisu"""
        return self.comments.count()
    
    def is_liked_by(self, user):
        """Sprawdza, czy przepis jest polubiony przez danego użytkownika"""
        if not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()
    
    def toggle_like(self, user):
        """Przełącza polubienie przepisu przez użytkownika. Zwraca True jeśli polubiono, False jeśli odklikano"""
        if not user.is_authenticated:
            return False
            
        like, created = RecipeLike.objects.get_or_create(user=user, recipe=self)
        
        if not created:
            # Jeśli polubienie już istniało, usuń je
            like.delete()
            return False
            
        return True
    
    def get_missing_ingredients(self, user):
        """Zwraca listę brakujących składników, które użytkownik musi dokupić,
        aby przygotować przepis"""
        if not user.is_authenticated:
            return []
        
        # Import lokalny, aby uniknąć cyklicznego importu
        from fridge.models import FridgeItem
        
        missing = []
        for ingredient_entry in self.ingredients.all():
            # Sprawdź każdy składnik przepisu
            if not FridgeItem.check_ingredient_availability(
                user, 
                ingredient_entry.ingredient,
                ingredient_entry.amount,
                ingredient_entry.unit
            ):
                # Dodaj do listy brakujących
                missing.append(ingredient_entry)
        
        return missing
    
    def can_be_prepared_with_available_ingredients(self, user):
        """Sprawdza, czy przepis może być przygotowany z dostępnych składników"""
        return self.get_missing_ingredients(user) == []
    
    def scale_to_servings(self, target_servings):
        """Zwraca listę składników przepisu przeskalowaną do podanej liczby porcji"""
        try:
            target_servings = float(target_servings)
            
            if target_servings <= 0:
                raise ValueError("Liczba porcji musi być większa od zera")
                
            ratio = target_servings / float(self.servings)
            scaled_ingredients = []
            
            for ing in self.ingredients.all():
                # Zapewnij, że wartości są typu float
                original_amount = float(ing.amount)
                scaled_amount = original_amount * ratio
                
                scaled_ingredients.append({
                    'ingredient': ing.ingredient,
                    'amount': scaled_amount,
                    'unit': ing.unit,
                    'original_amount': original_amount
                })
                
            return scaled_ingredients
        except (ValueError, TypeError) as e:
            raise ValueError(f"Błąd skalowania przepisu: {str(e)}")

    @property
    def average_rating(self):
        """Zwraca średnią ocenę przepisu"""
        ratings = self.ratings.all()
        if not ratings:
            return 0
        return sum(rating.rating for rating in ratings) / len(ratings)
    
    @property
    def ratings_count(self):
        """Zwraca liczbę ocen dla przepisu"""
        return self.ratings.count()
    
    def get_user_rating(self, user):
        """Zwraca ocenę danego użytkownika dla przepisu"""
        if not user.is_authenticated:
            return None
        try:
            return self.ratings.get(user=user)
        except RecipeRating.DoesNotExist:
            return None

    def get_rating_stats(self):
        """Zwraca statystyki ocen przepisu (ile ocen poszczególnych wartości)"""
        stats = {i: 0 for i in range(1, 6)}  # Słownik z kluczami 1-5 i wartościami początkowymi 0
        
        for rating in self.ratings.all():
            stats[rating.rating] += 1
            
        # Dodajemy dodatkowe informacje: łączna liczba ocen i procenty dla każdej oceny
        total = sum(stats.values())
        
        if total > 0:
            percentages = {score: (count / total) * 100 for score, count in stats.items()}
        else:
            percentages = {score: 0 for score in stats.keys()}
            
        return {
            'counts': stats,
            'total': total,
            'percentages': percentages
        }

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
        return f"{self.user.username} lubi {self.recipe.title}"

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

class RecipeStep(models.Model):
    """Model do przechowywania kroków przygotowania przepisu"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps', verbose_name="Przepis")
    step_number = models.PositiveIntegerField(verbose_name="Numer kroku")
    description = models.TextField(verbose_name="Opis kroku")
    
    class Meta:
        verbose_name = "Krok przepisu"
        verbose_name_plural = "Kroki przepisu"
        ordering = ['recipe', 'step_number']
        unique_together = ('recipe', 'step_number')
    
    def __str__(self):
        return f"{self.recipe.title} - Krok {self.step_number}"

class RecipeImage(models.Model):
    """Model do przechowywania zdjęć przepisu"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='images', verbose_name="Przepis")
    image = models.ImageField(upload_to='recipes/', verbose_name="Zdjęcie")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="Opis zdjęcia")
    is_main = models.BooleanField(default=False, verbose_name="Zdjęcie główne")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    
    class Meta:
        verbose_name = "Zdjęcie przepisu"
        verbose_name_plural = "Zdjęcia przepisu"
        ordering = ['-is_main', '-uploaded_at']
    
    def __str__(self):
        return f"Zdjęcie {self.id} dla {self.recipe.title}"
    
    def save(self, *args, **kwargs):
        """Upewnij się, że jest tylko jedno główne zdjęcie dla przepisu"""
        if self.is_main:
            # Usuń flagę głównego zdjęcia z innych zdjęć tego przepisu
            RecipeImage.objects.filter(recipe=self.recipe).exclude(id=self.id).update(is_main=False)
        super().save(*args, **kwargs)

class IngredientUnit(models.Model):
    """Model łączący składnik z dozwolonymi dla niego jednostkami miary"""
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE, related_name='allowed_units')
    unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE)
    is_default = models.BooleanField(default=False, verbose_name="Domyślna jednostka")
    conversion_info = models.CharField(max_length=100, blank=True, verbose_name="Informacja o przeliczniku")

    class Meta:
        verbose_name = "Jednostka składnika"
        verbose_name_plural = "Jednostki składników"
        unique_together = ['ingredient', 'unit']

    def __str__(self):
        return f"{self.ingredient.name} - {self.unit.name}"

    def save(self, *args, **kwargs):
        # Upewnij się, że tylko jedna jednostka jest domyślna dla składnika
        if self.is_default:
            IngredientUnit.objects.filter(ingredient=self.ingredient).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

class IngredientConversion(models.Model):
    """
    Model przechowujący współczynniki konwersji dla konkretnych składników.
    Pozwala na definiowanie tabeli konwersji między różnymi jednostkami dla danego składnika.
    """
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE, related_name='conversions', verbose_name="Składnik")
    from_unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, related_name='from_conversions', verbose_name="Z jednostki")
    to_unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, related_name='to_conversions', verbose_name="Na jednostkę")
    ratio = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Współczynnik konwersji")
    description = models.CharField(max_length=200, blank=True, verbose_name="Dodatkowy opis")
    is_exact = models.BooleanField(default=True, verbose_name="Dokładna konwersja")
    
    class Meta:
        verbose_name = "Konwersja składnika"
        verbose_name_plural = "Konwersje składników"
        unique_together = ['ingredient', 'from_unit', 'to_unit']
        ordering = ['ingredient__name', 'from_unit__name', 'to_unit__name']
    
    def __str__(self):
        return f"{self.ingredient.name}: {self.from_unit.symbol} → {self.to_unit.symbol} ({self.ratio})"
    
    def convert(self, amount):
        """
        Konwertuje podaną ilość z jednostki źródłowej na docelową używając współczynnika konwersji.
        """
        from decimal import Decimal
        try:
            amount = Decimal(str(amount))
            return amount * self.ratio
        except (ValueError, TypeError):
            raise ValueError(f"Niepoprawna wartość do konwersji: {amount}")
    
    @classmethod
    def get_conversion_ratio(cls, ingredient, from_unit, to_unit):
        """
        Zwraca współczynnik konwersji między dwiema jednostkami dla danego składnika.
        Jeśli bezpośrednia konwersja nie istnieje, próbuje znaleźć pośrednią lub odwrotną.
        """
        # Sprawdź, czy jednostki nie są takie same
        if from_unit == to_unit:
            return 1
            
        # Próba znalezienia bezpośredniej konwersji
        try:
            conversion = cls.objects.get(ingredient=ingredient, from_unit=from_unit, to_unit=to_unit)
            return conversion.ratio
        except cls.DoesNotExist:
            pass
            
        # Próba znalezienia odwrotnej konwersji
        try:
            conversion = cls.objects.get(ingredient=ingredient, from_unit=to_unit, to_unit=from_unit)
            from decimal import Decimal
            if conversion.ratio == 0:
                raise ValueError("Współczynnik konwersji nie może być równy zero")
            return Decimal(1) / conversion.ratio
        except cls.DoesNotExist:
            pass
        
        # Jeśli nie znaleziono bezpośredniej ani odwrotnej konwersji,
        # próbujemy znaleźć pośrednią przez jednostki podstawowe
        base_unit = None
        
        # Ustal jednostkę podstawową na podstawie typu jednostek
        if from_unit.type == 'weight' and to_unit.type == 'weight':
            # Dla wagi podstawową jednostką są gramy
            try:
                base_unit = MeasurementUnit.objects.get(symbol='g')
            except MeasurementUnit.DoesNotExist:
                pass
        elif from_unit.type == 'volume' and to_unit.type == 'volume':
            # Dla objętości podstawową jednostką są mililitry
            try:
                base_unit = MeasurementUnit.objects.get(symbol='ml')
            except MeasurementUnit.DoesNotExist:
                pass
        
        if base_unit:
            # Próba konwersji przez jednostkę podstawową
            try:
                from_to_base = cls.get_conversion_ratio(ingredient, from_unit, base_unit)
                base_to_to = cls.get_conversion_ratio(ingredient, base_unit, to_unit)
                return from_to_base * base_to_to
            except:
                pass
        
        # Jeśli wszystkie metody zawiodły, zgłoś brak możliwości konwersji
        raise ValueError(f"Brak możliwości konwersji z {from_unit.symbol} na {to_unit.symbol} dla {ingredient.name}")

class ConversionTable(models.Model):
    """
    Model predefiniowanej tablicy konwersji, która może być przypisana do różnych składników.
    Zawiera zestaw konwersji dla różnych typów produktów (np. mąka, płyny, owoce).
    """
    name = models.CharField(max_length=100, verbose_name="Nazwa tablicy")
    description = models.TextField(blank=True, verbose_name="Opis")
    category = models.ForeignKey(IngredientCategory, on_delete=models.CASCADE, related_name='conversion_tables',
                                verbose_name="Kategoria produktów", null=True)
    is_for_liquids = models.BooleanField(default=False, verbose_name="Dla płynów", 
                                       help_text="Zaznacz, jeśli ta tablica jest przeznaczona dla produktów płynnych")
    is_approved = models.BooleanField(default=True, verbose_name="Zatwierdzona")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='created_conversion_tables', verbose_name="Utworzona przez")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data utworzenia")
    
    class Meta:
        verbose_name = "Tablica konwersji"
        verbose_name_plural = "Tablice konwersji"
        ordering = ['category__name', 'name']
    
    def __str__(self):
        category_name = self.category.name if self.category else "Bez kategorii"
        return f"{self.name} ({category_name})"
    
    @property
    def product_type(self):
        """Dla zachowania kompatybilności ze starym kodem"""
        return self.category.name if self.category else "Inne"

class ConversionTableEntry(models.Model):
    """
    Pojedynczy wpis w predefiniowanej tablicy konwersji.
    """
    table = models.ForeignKey(ConversionTable, on_delete=models.CASCADE, related_name='entries', 
                             verbose_name="Tablica konwersji")
    from_unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, related_name='+', 
                                 verbose_name="Z jednostki")
    to_unit = models.ForeignKey(MeasurementUnit, on_delete=models.CASCADE, related_name='+', 
                               verbose_name="Na jednostkę")
    ratio = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Współczynnik konwersji")
    is_exact = models.BooleanField(default=True, verbose_name="Dokładna konwersja")
    notes = models.CharField(max_length=200, blank=True, verbose_name="Uwagi")
    
    class Meta:
        verbose_name = "Wpis tablicy konwersji"
        verbose_name_plural = "Wpisy tablicy konwersji"
        unique_together = ['table', 'from_unit', 'to_unit']
        ordering = ['table', 'from_unit__name', 'to_unit__name']
    
    def __str__(self):
        return f"{self.from_unit.symbol} → {self.to_unit.symbol} ({self.ratio})"

class UserIngredient(models.Model):
    """
    Model składnika zgłoszonego przez użytkownika, oczekującego na zatwierdzenie.
    """
    name = models.CharField(max_length=100, verbose_name="Nazwa składnika")
    category = models.ForeignKey(IngredientCategory, on_delete=models.CASCADE, related_name='+', 
                                verbose_name="Kategoria")
    description = models.TextField(blank=True, null=True, verbose_name="Opis")
    default_unit = models.ForeignKey(MeasurementUnit, on_delete=models.SET_NULL, null=True, 
                                    related_name='+', verbose_name="Domyślna jednostka")
    conversion_table = models.ForeignKey(ConversionTable, on_delete=models.SET_NULL, null=True, 
                                         related_name='user_ingredients', verbose_name="Tablica konwersji")
    density = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, 
                                 verbose_name="Gęstość [g/ml]")
    piece_weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, 
                                      verbose_name="Waga sztuki [g]")
    unit_type = models.CharField(max_length=20, choices=[
        ('weight_only', 'Tylko waga (g, kg)'),
        ('volume_only', 'Tylko objętość (ml, l)'),
        ('piece_only', 'Tylko sztuki'),
        ('weight_volume', 'Waga i objętość'),
        ('weight_piece', 'Waga i sztuki'),
        ('weight_spoon', 'Waga i łyżki'),
        ('volume_spoon', 'Objętość i łyżki'),
        ('all', 'Wszystkie jednostki')
    ], default='weight_only', verbose_name="Dozwolone jednostki")
    
    # Dane zgłoszenia
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_ingredients', 
                            verbose_name="Zgłoszone przez")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Data zgłoszenia")
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Oczekujący'),
        ('approved', 'Zatwierdzony'),
        ('rejected', 'Odrzucony')
    ], default='pending', verbose_name="Status")
    admin_notes = models.TextField(blank=True, verbose_name="Uwagi administratora")
    
    class Meta:
        verbose_name = "Składnik użytkownika"
        verbose_name_plural = "Składniki użytkowników"
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.name} (zgłoszony przez {self.user.username})"
    
    def approve(self, admin_user=None):
        """
        Zatwierdza składnik i tworzy z niego normalny składnik w bazie.
        """
        # Utwórz nowy składnik na podstawie danych z UserIngredient
        ingredient = Ingredient.objects.create(
            name=self.name,
            category=self.category,
            description=self.description,
            default_unit=self.default_unit,
            density=self.density,
            piece_weight=self.piece_weight,
            unit_type=self.unit_type
        )
        
        # Jeśli przypisano tablicę konwersji, utwórz wpisy IngredientConversion
        if self.conversion_table:
            for entry in self.conversion_table.entries.all():
                IngredientConversion.objects.create(
                    ingredient=ingredient,
                    from_unit=entry.from_unit,
                    to_unit=entry.to_unit,
                    ratio=entry.ratio,
                    is_exact=entry.is_exact,
                    description=f"Z tablicy konwersji: {self.conversion_table.name}"
                )
                
        # Aktualizuj status na zatwierdzony
        self.status = 'approved'
        self.save()
        
        return ingredient
    
    def reject(self, reason=None, admin_user=None):
        """
        Odrzuca składnik
        """
        self.status = 'rejected'
        if reason:
            self.admin_notes = reason
        self.save()

class RecipeRating(models.Model):
    """Model do przechowywania ocen przepisów (gwiazdki)"""
    RATING_CHOICES = [
        (1, '1 - Bardzo słabo'),
        (2, '2 - Słabo'),
        (3, '3 - Przeciętnie'),
        (4, '4 - Dobrze'),
        (5, '5 - Bardzo dobrze')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_ratings', verbose_name="Użytkownik")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ratings', verbose_name="Przepis")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name="Ocena")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data aktualizacji")
    comment = models.TextField(blank=True, null=True, verbose_name="Komentarz do oceny")
    
    class Meta:
        verbose_name = "Ocena przepisu"
        verbose_name_plural = "Oceny przepisów"
        unique_together = ('user', 'recipe')  # Użytkownik może dać tylko jedną ocenę dla przepisu
        
    def __str__(self):
        return f"Ocena {self.rating}/5 od {self.user.username} dla {self.recipe.title}"

    @property
    def helpful_count(self):
        """Zwraca liczbę oznaczeń oceny jako przydatna"""
        return self.helpful_marks.count()
    
    def is_helpful_for(self, user):
        """Sprawdza, czy ocena jest oznaczona jako przydatna przez danego użytkownika"""
        if not user.is_authenticated:
            return False
        return self.helpful_marks.filter(user=user).exists()
    
    def toggle_helpful(self, user):
        """Przełącza oznaczenie oceny jako przydatna/nieprzydatna przez użytkownika"""
        if not user.is_authenticated:
            return False
            
        helpful, created = RatingHelpful.objects.get_or_create(user=user, rating=self)
        
        if not created:
            # Jeśli oznaczenie już istniało, usuń je
            helpful.delete()
            return False
            
        return True

class RatingHelpful(models.Model):
    """Model do przechowywania informacji o tym, czy ocena była przydatna dla użytkownika"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='helpful_ratings', verbose_name="Użytkownik")
    rating = models.ForeignKey(RecipeRating, on_delete=models.CASCADE, related_name='helpful_marks', verbose_name="Ocena")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data dodania")
    
    class Meta:
        verbose_name = "Przydatna ocena"
        verbose_name_plural = "Przydatne oceny"
        unique_together = ('user', 'rating')  # Użytkownik może oznaczyć ocenę jako przydatną tylko raz
        
    def __str__(self):
        return f"Ocena {self.rating.id} oznaczona jako przydatna przez {self.user.username}" 