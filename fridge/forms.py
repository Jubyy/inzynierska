from django import forms
from .models import FridgeItem
from recipes.models import Ingredient, MeasurementUnit, IngredientCategory
from django.forms import formset_factory
from django.core.exceptions import ValidationError

class FridgeItemForm(forms.ModelForm):
    """Formularz do dodawania i edycji produktów w lodówce"""
    class Meta:
        model = FridgeItem
        fields = ['ingredient', 'amount', 'unit', 'expiry_date']
        widgets = {
            'ingredient': forms.Select(attrs={
                'class': 'form-control select2-ingredient',
                'data-placeholder': 'Wpisz lub wybierz składnik...'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': 'any',
                'placeholder': 'Podaj ilość'
            }),
            'unit': forms.Select(attrs={
                'class': 'form-control select2-unit',
                'data-placeholder': 'Wybierz jednostkę'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
        labels = {
            'ingredient': 'Składnik',
            'amount': 'Ilość',
            'unit': 'Jednostka',
            'expiry_date': 'Data ważności'
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pole składnika będzie wypełniane przez Select2 AJAX
        self.fields['ingredient'].queryset = Ingredient.objects.all()
        self.fields['ingredient'].widget.attrs['data-ajax--url'] = '/fridge/ajax/ingredient-search/'
        
        # Pole jednostki będzie aktualizowane dynamicznie na podstawie wybranego składnika
        self.fields['unit'].queryset = MeasurementUnit.objects.all()
        
        # Jeśli edytujemy istniejący obiekt, załaduj kompatybilne jednostki
        if self.instance and self.instance.pk and self.instance.ingredient:
            # Pobierz kompatybilne jednostki dla tego składnika
            self.fields['unit'].queryset = self.instance.ingredient.compatible_units.all()
            if not self.fields['unit'].queryset.exists() and self.instance.ingredient.default_unit:
                self.fields['unit'].queryset = MeasurementUnit.objects.filter(pk=self.instance.ingredient.default_unit.pk)
            
            # Podczas edycji, zamiast blokować jednostkę jako disabled/readonly,
            # dodajmy tylko ukryte pole, które zawsze będzie przesyłane
            self.fields['hidden_unit'] = forms.IntegerField(
                initial=self.instance.unit.pk,
                widget=forms.HiddenInput(),
                required=False
            )
            
            # Ustawmy początkową wartość pola jednostki
            self.initial['unit'] = self.instance.unit.pk
            
            # Dodajmy klasę CSS, która pozwoli stylizować to pole jako "tylko do odczytu"
            self.fields['unit'].widget.attrs['class'] += ' readonly-select'
            self.fields['unit'].widget.attrs['data-original-value'] = self.instance.unit.pk
    
    def clean(self):
        cleaned_data = super().clean()
        ingredient = cleaned_data.get('ingredient')
        unit = cleaned_data.get('unit')
        amount = cleaned_data.get('amount')
        
        # Jeśli edytujemy istniejący obiekt i pole jednostki jest wyłączone,
        # użyj wartości z ukrytego pola lub bezpośrednio z instancji
        if self.instance and self.instance.pk:
            hidden_unit = self.data.get('hidden_unit')
            if hidden_unit:
                try:
                    unit = MeasurementUnit.objects.get(pk=hidden_unit)
                    cleaned_data['unit'] = unit
                except (MeasurementUnit.DoesNotExist, ValueError):
                    # Jeśli nie znaleziono jednostki z ukrytego pola, użyj jednostki z instancji
                    if self.instance.unit:
                        unit = self.instance.unit
                        cleaned_data['unit'] = unit
            elif not unit and self.instance.unit:
                # Jeśli brak jednostki w danych, ale mamy ją w instancji
                unit = self.instance.unit
                cleaned_data['unit'] = unit
        
        if ingredient and amount:
            # Jeśli brakuje jednostki przy edycji, dodaj błąd
            if not unit:
                self.add_error('unit', 'To pole jest wymagane.')
                return cleaned_data
                
            # Lista jednostek wymagających liczb całkowitych
            whole_number_units = ['szt', 'sztuka', 'garść', 'opakowanie']
            
            # Sprawdź, czy dla jednostek wymagających liczb całkowitych podano liczbę całkowitą
            if unit.symbol in whole_number_units and not float(amount).is_integer():
                # Zamiast dodawać błąd, automatycznie zaokrąglamy wartość
                cleaned_data['amount'] = round(float(amount))
                # Dodaj komunikat informujący użytkownika o automatycznym zaokrągleniu
                self.add_error('amount', f'Wartość została automatycznie zaokrąglona do {cleaned_data["amount"]} (jednostka wymaga liczby całkowitej).')
            
            # Sprawdź, czy wybrana jednostka jest kompatybilna ze składnikiem
            # Ale tylko dla nowo dodawanych produktów, nie dla edytowanych
            if not self.instance or not self.instance.pk:
                compatible_units = ingredient.compatible_units.all()
                if not compatible_units.exists() and ingredient.default_unit:
                    compatible_units = [ingredient.default_unit]
                
                if unit not in compatible_units:
                    # Zamiast dodawać błąd, dodaj jednostkę do kompatybilnych
                    ingredient.compatible_units.add(unit)
                    # Dodaj informację dla użytkownika
                    self.add_error('unit', f'Automatycznie dodano {unit.name} jako kompatybilną jednostkę dla {ingredient.name}.')
        
        return cleaned_data

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
    ingredient = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2-ingredient ingredient-select'})
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Przygotowanie pogrupowanych opcji składników według kategorii
        ingredient_choices = []
        
        # Dodaj pustą opcję
        ingredient_choices.append(('', '---------'))
        
        # Pobierz wszystkie kategorie składników
        categories = IngredientCategory.objects.all().order_by('name')
        
        # Dla każdej kategorii, pobierz jej składniki
        for category in categories:
            category_ingredients = [(i.id, i.name) for i in Ingredient.objects.filter(category=category).order_by('name')]
            if category_ingredients:  # Dodaj tylko jeśli kategoria ma składniki
                ingredient_choices.append((category.name, category_ingredients))
        
        # Ustaw pogrupowane opcje dla pola ingredient
        self.fields['ingredient'].choices = ingredient_choices

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
