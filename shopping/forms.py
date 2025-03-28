from django import forms
from .models import ShoppingList, ShoppingItem
from recipes.models import Ingredient, MeasurementUnit, Recipe
from django.forms import formset_factory

class ShoppingListForm(forms.ModelForm):
    """Formularz do tworzenia i edycji list zakupów"""
    class Meta:
        model = ShoppingList
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa listy zakupów'})
        }
        labels = {
            'name': 'Nazwa listy'
        }

class ShoppingItemForm(forms.ModelForm):
    """Formularz do dodawania i edycji pozycji na liście zakupów"""
    class Meta:
        model = ShoppingItem
        fields = ['ingredient', 'amount', 'unit', 'note']
        widgets = {
            'ingredient': forms.Select(attrs={'class': 'form-control select2'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcjonalna notatka'})
        }
        labels = {
            'ingredient': 'Składnik',
            'amount': 'Ilość',
            'unit': 'Jednostka',
            'note': 'Notatka'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Sortowanie składników alfabetycznie
        self.fields['ingredient'].queryset = Ingredient.objects.all().order_by('name')

# Formset do dodawania wielu pozycji jednocześnie
ShoppingItemFormSet = formset_factory(
    ShoppingItemForm,
    extra=5,  # Liczba pustych formularzy
    can_delete=False
)

class RecipeToShoppingListForm(forms.Form):
    """Formularz do tworzenia listy zakupów na podstawie przepisu"""
    recipe = forms.ModelChoiceField(
        queryset=Recipe.objects.all().order_by('title'),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        label='Wybierz przepis'
    )
    
    servings = forms.IntegerField(
        initial=4,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        label='Liczba porcji'
    )
    
    create_new_list = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Utwórz nową listę zakupów'
    )
    
    existing_list = forms.ModelChoiceField(
        queryset=ShoppingList.objects.none(),  # Będzie ustawione w __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='lub dodaj do istniejącej listy'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Filtruj listy zakupów tylko dla zalogowanego użytkownika
            self.fields['existing_list'].queryset = ShoppingList.objects.filter(
                user=self.user, 
                is_completed=False
            ).order_by('-created_at')

class MissingIngredientsForm(forms.Form):
    """Formularz do dodawania brakujących składników do listy zakupów"""
    shopping_list = forms.ModelChoiceField(
        queryset=ShoppingList.objects.none(),  # Będzie ustawione w __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Wybierz istniejącą listę zakupów'
    )
    
    create_new_list = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Utwórz nową listę zakupów'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Filtruj listy zakupów tylko dla zalogowanego użytkownika
            self.fields['shopping_list'].queryset = ShoppingList.objects.filter(
                user=self.user, 
                is_completed=False
            ).order_by('-created_at')
