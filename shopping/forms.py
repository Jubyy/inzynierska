from django import forms
from .models import ShoppingList, ShoppingItem
from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory
from django.forms import formset_factory

class ShoppingListForm(forms.ModelForm):
    """Formularz do tworzenia i edycji list zakupów"""
    class Meta:
        model = ShoppingList
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nazwa listy'
        }

class ShoppingItemForm(forms.ModelForm):
    """Formularz do dodawania i edycji pozycji na liście zakupów"""
    # Ukryte pola do przechowywania oryginalnych wartości podczas edycji
    hidden_ingredient = forms.IntegerField(required=False, widget=forms.HiddenInput())
    hidden_unit = forms.IntegerField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = ShoppingItem
        fields = ['ingredient', 'amount', 'unit', 'note', 'shopping_list']
        widgets = {
            'ingredient': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'shopping_list': forms.HiddenInput(),
        }
        labels = {
            'ingredient': 'Składnik',
            'amount': 'Ilość',
            'unit': 'Jednostka',
            'note': 'Notatka'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Usuwamy standardowy widget dla składnika, będziemy używać Select2 z grupowaniem
        self.fields['ingredient'].widget = forms.Select(attrs={'class': 'form-control select2-ingredient'})
        
        # Przygotowanie pogrupowanych opcji składników według kategorii
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
        
        # Opcjonalny atrybut readonly dla składnika i jednostki podczas edycji
        if self.instance and self.instance.pk:
            # Jeśli edytujemy istniejący obiekt, ustawiamy tylko zmianę ilości i notatki
            self.fields['ingredient'].widget.attrs['readonly'] = True
            self.fields['ingredient'].widget.attrs['class'] += ' bg-light'
            self.fields['unit'].widget.attrs['readonly'] = True
            self.fields['unit'].widget.attrs['class'] += ' bg-light'
            
            # Inicjalizacja ukrytych pól z istniejących wartości
            self.initial['hidden_ingredient'] = self.instance.ingredient_id
            self.initial['hidden_unit'] = self.instance.unit_id
        
    def clean(self):
        cleaned_data = super().clean()
        
        # Jeśli to edycja istniejącego obiektu, używamy ukrytych pól
        if self.instance and self.instance.pk:
            try:
                # Pobierz wartości z ukrytych pól lub z formularza
                hidden_ingredient_id = self.data.get('hidden_ingredient') or self.initial.get('hidden_ingredient')
                hidden_unit_id = self.data.get('hidden_unit') or self.initial.get('hidden_unit')
                
                if hidden_ingredient_id:
                    # Pobieramy oryginalne wartości z bazy danych
                    ingredient = Ingredient.objects.get(pk=hidden_ingredient_id)
                    cleaned_data['ingredient'] = ingredient
                else:
                    # Fallback do oryginalnej wartości z instancji
                    cleaned_data['ingredient'] = self.instance.ingredient
                
                if hidden_unit_id:
                    unit = MeasurementUnit.objects.get(pk=hidden_unit_id)
                    cleaned_data['unit'] = unit
                else:
                    # Fallback do oryginalnej wartości z instancji
                    cleaned_data['unit'] = self.instance.unit
                    
            except (Ingredient.DoesNotExist, MeasurementUnit.DoesNotExist):
                # Jeśli nie można pobrać obiektu, używamy oryginalnych wartości z instancji
                cleaned_data['ingredient'] = self.instance.ingredient
                cleaned_data['unit'] = self.instance.unit
        
        # Jeśli jednostka to sztuka, upewnij się, że ilość jest liczbą całkowitą
        unit = cleaned_data.get('unit')
        amount = cleaned_data.get('amount')
        
        if unit and unit.type == 'piece' and amount is not None:
            cleaned_data['amount'] = round(amount)
        
        return cleaned_data

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
