from django import forms
from django.forms import inlineformset_factory
from .models import Recipe, RecipeIngredient, RecipeCategory, Ingredient, MeasurementUnit

class RecipeForm(forms.ModelForm):
    """Formularz do tworzenia i edycji przepisów"""
    class Meta:
        model = Recipe
        fields = ['title', 'description', 'instructions', 'servings', 
                 'preparation_time', 'image', 'categories']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa przepisu'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Krótki opis przepisu'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Instrukcje przygotowania'}),
            'servings': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Czas w minutach'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-control select2'})
        }
        labels = {
            'title': 'Tytuł',
            'description': 'Opis',
            'instructions': 'Instrukcje przygotowania',
            'servings': 'Liczba porcji',
            'preparation_time': 'Czas przygotowania (minuty)',
            'image': 'Zdjęcie',
            'categories': 'Kategorie'
        }

class RecipeIngredientForm(forms.ModelForm):
    """Formularz do dodawania składników do przepisu"""
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2 ingredient-select'}),
        label='Składnik'
    )
    
    amount = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
        label='Ilość'
    )
    
    unit = forms.ModelChoiceField(
        queryset=MeasurementUnit.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control select2 unit-select'}),
        label='Jednostka'
    )
    
    class Meta:
        model = RecipeIngredient
        fields = ['ingredient', 'amount', 'unit']

# Formset do zarządzania wieloma składnikami dla przepisu
RecipeIngredientFormSet = inlineformset_factory(
    Recipe, 
    RecipeIngredient,
    form=RecipeIngredientForm,
    extra=3,  # Liczba pustych formularzy
    can_delete=True,  # Możliwość usuwania składników
    min_num=1,  # Minimalnie jeden składnik
    validate_min=True,  # Walidacja minimalnej liczby składników
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
        fields = ['name', 'category', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }
        labels = {
            'name': 'Nazwa składnika',
            'category': 'Kategoria',
            'description': 'Opis'
        }

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
