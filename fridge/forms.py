from django import forms
from .models import FridgeItem
from recipes.models import Ingredient, MeasurementUnit
from django.forms import formset_factory

class FridgeItemForm(forms.ModelForm):
    """Formularz do dodawania i edycji produktów w lodówce"""
    class Meta:
        model = FridgeItem
        fields = ['ingredient', 'amount', 'unit', 'expiry_date']
        widgets = {
            'ingredient': forms.Select(attrs={'class': 'form-control select2'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        }
        labels = {
            'ingredient': 'Składnik',
            'amount': 'Ilość',
            'unit': 'Jednostka',
            'expiry_date': 'Data ważności'
        }
    
    def __init__(self, *args, **kwargs):
        # Pobierz użytkownika z parametrów (opcjonalnie)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Sortowanie składników alfabetycznie
        self.fields['ingredient'].queryset = Ingredient.objects.all().order_by('name')

class FridgeSearchForm(forms.Form):
    """Formularz do wyszukiwania produktów w lodówce"""
    q = forms.CharField(
        required=False,
        label='Szukaj produktu',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wpisz nazwę produktu...'})
    )
    
    SORT_CHOICES = [
        ('ingredient__name', 'Nazwa (A-Z)'),
        ('-ingredient__name', 'Nazwa (Z-A)'),
        ('expiry', 'Data ważności (rosnąco)'),
        ('-expiry', 'Data ważności (malejąco)'),
        ('amount', 'Ilość (rosnąco)'),
        ('-amount', 'Ilość (malejąco)')
    ]
    
    sort = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        label='Sortowanie',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class BulkItemForm(forms.Form):
    """Formularz dla pojedynczego produktu w formularzu zbiorczym"""
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2 ingredient-select'})
    )
    
    amount = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': 0.01, 'placeholder': 'Ilość'})
    )
    
    unit = forms.ModelChoiceField(
        queryset=MeasurementUnit.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control unit-select'})
    )
    
    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

# Formset do zbiorczego dodawania produktów
BulkItemFormSet = formset_factory(
    BulkItemForm,
    extra=5,  # Liczba pustych formularzy
    can_delete=False
)

class BulkAddForm(forms.Form):
    """Formularz do zbiorczego dodawania produktów do lodówki"""
    # Ten formularz jest kontenerem dla formsetów BulkItemFormSet
    # Używany jest do zbiorczej walidacji
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Sprawdź, czy co najmniej jeden produkt został dodany
        ingredients = self.data.getlist('ingredients')
        amounts = self.data.getlist('amounts')
        units = self.data.getlist('units')
        
        valid_items = 0
        for i in range(len(ingredients)):
            if ingredients[i] and amounts[i] and units[i]:
                valid_items += 1
        
        if valid_items == 0:
            raise forms.ValidationError("Dodaj co najmniej jeden produkt do lodówki.")
        
        return cleaned_data
