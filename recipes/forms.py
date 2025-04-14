from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Recipe, RecipeIngredient, RecipeCategory, Ingredient, MeasurementUnit, IngredientCategory, Comment, ConversionTable, ConversionTableEntry, RecipeRating
from django.db import models

class RecipeForm(forms.ModelForm):
    """Formularz do tworzenia i edycji przepisów"""
    class Meta:
        model = Recipe
        fields = ['title', 'categories', 'description', 'instructions', 'servings', 'preparation_time', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'categories': forms.SelectMultiple(attrs={
                'class': 'form-control categories-select',
                'data-placeholder': 'Wybierz kategorie'
            }),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control'}),
            'servings': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categories'].queryset = RecipeCategory.objects.all().order_by('name')
        self.fields['categories'].required = True
        self.fields['title'].label = 'Tytuł'
        self.fields['categories'].label = 'Kategorie'
        self.fields['description'].label = 'Opis'
        self.fields['instructions'].label = 'Instrukcje przygotowania'
        self.fields['servings'].label = 'Liczba porcji'
        self.fields['preparation_time'].label = 'Czas przygotowania (minuty)'
        self.fields['image'].label = 'Zdjęcie'

class RecipeIngredientForm(forms.ModelForm):
    """Formularz dla składnika przepisu"""
    class Meta:
        model = RecipeIngredient
        fields = ['ingredient', 'amount', 'unit']
        widgets = {
            'ingredient': forms.Select(attrs={'class': 'form-control select2-ingredient'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
            'unit': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Grupowanie składników według kategorii
        ingredient_choices = []
        
        # Pobierz wszystkie kategorie składników
        categories = IngredientCategory.objects.all().order_by('name')
        
        # Dla każdej kategorii, pobierz jej składniki
        for category in categories:
            category_ingredients = [(i.id, i.name) for i in Ingredient.objects.filter(category=category).order_by('name')]
            if category_ingredients:  # Dodaj tylko jeśli kategoria ma składniki
                ingredient_choices.append((category.name, category_ingredients))
        
        # Ustaw pogrupowane opcje dla pola ingredient
        self.fields['ingredient'].choices = ingredient_choices
    
    def clean(self):
        cleaned_data = super().clean()
        ingredient = cleaned_data.get('ingredient')
        unit = cleaned_data.get('unit')
        amount = cleaned_data.get('amount')
        
        print(f"[DEBUG] RecipeIngredientForm.clean() - ingredient: {ingredient}, unit: {unit}, amount: {amount}")
        
        if ingredient and unit and amount:
            # Lista jednostek wymagających liczb całkowitych
            whole_number_units = ['szt', 'sztuka', 'garść', 'opakowanie']
            
            # Sprawdź, czy dla jednostek wymagających liczb całkowitych podano liczbę całkowitą
            if unit.symbol in whole_number_units and not float(amount).is_integer():
                print(f"[DEBUG] Błąd: Dla jednostki {unit.symbol} podano wartość niecałkowitą: {amount}")
                self.add_error('amount', 'Dla tej jednostki można podać tylko liczby całkowite.')
            
            # Sprawdź kompatybilność przez dwa mechanizmy:
            # 1. Bezpośrednio przypisane kompatybilne jednostki
            compatible_units = ingredient.compatible_units.all()
            print(f"[DEBUG] Bezpośrednio kompatybilne jednostki dla {ingredient.name}: {[u.name for u in compatible_units]}")
            
            # Jeśli nie ma bezpośrednio przypisanych jednostek, ale jest domyślna jednostka
            if not compatible_units.exists() and ingredient.default_unit:
                compatible_units = [ingredient.default_unit]
                print(f"[DEBUG] Brak kompatybilnych jednostek, ale istnieje domyślna: {ingredient.default_unit.name}")
            
            # 2. Dozwolone jednostki wg unit_type
            allowed_units = ingredient.get_allowed_units()
            print(f"[DEBUG] Dozwolone jednostki wg unit_type dla {ingredient.name}: {[u.name for u in allowed_units]}")
            
            # Jednostka jest kompatybilna, jeśli jest na liście kompatybilnych
            # LUB jeśli pasuje do dozwolonego typu jednostek dla składnika
            if unit not in compatible_units and unit not in allowed_units:
                print(f"[DEBUG] Jednostka {unit.name} nie jest kompatybilna ze składnikiem {ingredient.name}")
                print(f"[DEBUG] Unit type składnika: {ingredient.unit_type}, typ jednostki: {unit.type}")
                self.add_error('unit', 'Wybrana jednostka nie jest kompatybilna z tym składnikiem.')
            elif unit not in compatible_units and unit in allowed_units:
                # Jeśli jednostka jest dozwolona wg typu, ale nie ma jej na liście kompatybilnych,
                # automatycznie dodaj ją do kompatybilnych jednostek
                print(f"[DEBUG] Automatycznie dodaję jednostkę {unit.name} do kompatybilnych dla {ingredient.name}")
                ingredient.compatible_units.add(unit)
        
        return cleaned_data

class BaseRecipeIngredientFormSet(BaseInlineFormSet):
    """Bazowa klasa dla formsetów składników przepisu"""
    
    def clean(self):
        """
        Waliduje cały formset, sprawdzając czy wszystkie wymagane pola są wypełnione.
        """
        if any(self.errors):
            # Nie wykonuj walidacji, jeśli poszczególne formularze mają błędy
            return
        
        # Na wszelki wypadek inicjalizujemy cleaned_data jako pustą listę
        if not hasattr(self, 'cleaned_data'):
            self.cleaned_data = []
        
        # Sprawdzamy, czy wszystkie pola są wypełnione
        for form in self.forms:
            if form.has_changed() and not form.cleaned_data.get('DELETE', False):
                ingredient = form.cleaned_data.get('ingredient')
                amount = form.cleaned_data.get('amount')
                unit = form.cleaned_data.get('unit')
                
                if not ingredient or not amount or not unit:
                    form.add_error(None, 'Wszystkie pola składnika muszą być wypełnione.')

# Formset do zarządzania wieloma składnikami dla przepisu
RecipeIngredientFormSet = inlineformset_factory(
    Recipe, 
    RecipeIngredient,
    form=RecipeIngredientForm,
    formset=BaseRecipeIngredientFormSet,
    extra=1,  # Liczba pustych formularzy na początku
    can_delete=True,  # Możliwość usuwania składników
    min_num=0,  # Zmieniamy z 1 na 0, aby nie wymagać minimalnej liczby składników
    validate_min=False  # Wyłączamy walidację minimalnej liczby składników
)

class RecipeCategoryForm(forms.ModelForm):
    """Formularz do tworzenia kategorii przepisów"""
    class Meta:
        model = RecipeCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }
        labels = {
            'name': 'Nazwa kategorii',
            'description': 'Opis'
        }

class IngredientForm(forms.ModelForm):
    """Formularz do tworzenia składników"""
    class Meta:
        model = Ingredient
        fields = ['name', 'category', 'description', 'unit_type', 'default_unit', 'piece_weight', 'density']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unit_type': forms.Select(attrs={'class': 'form-control'}),
            'default_unit': forms.Select(attrs={'class': 'form-control'}),
            'piece_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'density': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
        }
        labels = {
            'name': 'Nazwa składnika',
            'category': 'Kategoria',
            'description': 'Opis',
            'unit_type': 'Dozwolone jednostki',
            'default_unit': 'Domyślna jednostka',
            'piece_weight': 'Waga sztuki [g]',
            'density': 'Gęstość [g/ml]'
        }
        help_texts = {
            'unit_type': 'Wybierz, jakie typy jednostek miary są dozwolone dla tego składnika',
            'piece_weight': 'Dla składników sprzedawanych na sztuki, podaj wagę jednej sztuki w gramach',
            'density': 'Dla płynów i składników sypkich, podaj gęstość w g/ml dla konwersji między wagą a objętością'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pole default_unit jest opcjonalne
        self.fields['default_unit'].required = False
        self.fields['piece_weight'].required = False
        self.fields['density'].required = False
        
        # Jeśli to edycja istniejącego składnika, filtruj jednostki wg unit_type
        if self.instance and self.instance.pk:
            if self.instance.unit_type:
                self.fields['default_unit'].queryset = self.instance.get_allowed_units()

class RecipeSearchForm(forms.Form):
    """Formularz do wyszukiwania przepisów"""
    q = forms.CharField(
        required=False,
        label='Szukaj przepisu',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wpisz nazwę przepisu lub składnik...'})
    )
    
    category = forms.ModelChoiceField(
        queryset=RecipeCategory.objects.all(),
        required=False,
        label='Kategoria',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    DIET_CHOICES = [
        ('', '---------'),
        ('vegetarian', 'Wegetariańskie'),
        ('vegan', 'Wegańskie')
    ]
    
    diet = forms.ChoiceField(
        choices=DIET_CHOICES,
        required=False,
        label='Dieta',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    available_only = forms.BooleanField(
        required=False,
        label='Tylko przepisy z dostępnych składników',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
class ServingsForm(forms.Form):
    """Formularz do zmiany liczby porcji"""
    servings = forms.IntegerField(
        min_value=1,
        label='Liczba porcji',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )

class CommentForm(forms.ModelForm):
    """Formularz do dodawania komentarzy do przepisów"""
    content = forms.CharField(
        label='',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Podziel się swoją opinią o tym przepisie...',
            'rows': 3
        })
    )
    
    class Meta:
        model = Comment
        fields = ['content']

class ConversionTableForm(forms.ModelForm):
    """Formularz do tworzenia i edycji tablicy konwersji"""
    class Meta:
        model = ConversionTable
        fields = ['name', 'description', 'category', 'is_for_liquids']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 
                                           'placeholder': 'np. Mąka pszenna, Mleko, Owoce...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 
                                                 'placeholder': 'Krótki opis dla jakiego rodzaju produktów jest ta tablica konwersji'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_for_liquids': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class ConversionEntryForm(forms.ModelForm):
    """Formularz dla pojedynczego wpisu w tablicy konwersji"""
    class Meta:
        model = ConversionTableEntry
        fields = ['from_unit', 'to_unit', 'ratio', 'is_exact', 'notes']
        widgets = {
            'from_unit': forms.Select(attrs={'class': 'form-select'}),
            'to_unit': forms.Select(attrs={'class': 'form-select'}),
            'ratio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0.0001',
                                              'placeholder': 'np. 15.0'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 
                                             'placeholder': 'np. Na podstawie pomiarów kuchennych'}),
            'is_exact': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class RecipeRatingForm(forms.ModelForm):
    """Formularz do oceniania przepisów"""
    class Meta:
        model = RecipeRating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Dodaj komentarz do oceny (opcjonalnie)',
                'rows': 3
            })
        }
        labels = {
            'rating': 'Ocena',
            'comment': 'Komentarz'
        }
