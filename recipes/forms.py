from django import forms
from django.forms import inlineformset_factory
from .models import Recipe, RecipeIngredient, RecipeCategory, Ingredient, MeasurementUnit, IngredientCategory, Comment, MealPlan
from datetime import date, timedelta
from django.db import models

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

# Formset do zarządzania wieloma składnikami dla przepisu
RecipeIngredientFormSet = inlineformset_factory(
    Recipe, 
    RecipeIngredient,
    form=RecipeIngredientForm,
    extra=1,  # Liczba pustych formularzy na początku
    can_delete=True,  # Możliwość usuwania składników
    min_num=1,  # Minimalnie jeden składnik
    validate_min=True  # Walidacja minimalnej liczby składników
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

class MealPlanForm(forms.ModelForm):
    """Formularz do dodawania/edycji zaplanowanych posiłków"""
    date = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': date.today().strftime('%Y-%m-%d')
        }),
        initial=date.today
    )
    
    class Meta:
        model = MealPlan
        fields = ['recipe', 'custom_name', 'date', 'meal_type', 'servings', 'notes', 'completed']
        widgets = {
            'recipe': forms.Select(attrs={'class': 'form-control select2', 'required': False}),
            'custom_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Własna nazwa posiłku'}),
            'meal_type': forms.Select(attrs={'class': 'form-control'}),
            'servings': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Opcjonalne notatki do posiłku...'}),
            'completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Ograniczenie wyboru przepisów do tych utworzonych przez użytkownika lub publicznych
            self.fields['recipe'].queryset = Recipe.objects.filter(
                models.Q(author=user) | models.Q(is_public=True)
            ).order_by('title')
            
        # Dodajemy pole recipe jako opcjonalne
        self.fields['recipe'].required = False
        
    def clean(self):
        cleaned_data = super().clean()
        recipe = cleaned_data.get('recipe')
        custom_name = cleaned_data.get('custom_name')
        
        # Sprawdź, czy podano albo przepis, albo własną nazwę
        if not recipe and not custom_name:
            raise forms.ValidationError("Musisz podać przepis lub własną nazwę posiłku.")
            
        return cleaned_data

class MealPlanWeekForm(forms.Form):
    """Formularz do wyboru tygodnia do wyświetlenia planu posiłków"""
    start_date = forms.DateField(
        label="Tydzień rozpoczynający się od",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        initial=date.today
    )
    
    def clean_start_date(self):
        """Upewnij się, że data rozpoczęcia to poniedziałek"""
        start_date = self.cleaned_data['start_date']
        # Jeśli nie jest poniedziałkiem, zaokrąglij do poprzedzającego poniedziałku
        if start_date.weekday() != 0:  # 0 = poniedziałek
            days_to_subtract = start_date.weekday()
            start_date = start_date - timedelta(days=days_to_subtract)
        return start_date
