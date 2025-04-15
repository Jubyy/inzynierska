from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
import json
import requests
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher
import csv

from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory, IngredientConversion
from .models import FridgeItem, ExpiryNotification
from .forms import FridgeItemForm, BulkAddForm, FridgeSearchForm, BulkItemFormSet

@login_required
def fridge_dashboard(request):
    """
    Dashboard lodówki - pokazuje statystyki i informacje o produktach
    """
    # Pobierz wszystkie produkty z lodówki użytkownika
    fridge_items = FridgeItem.objects.filter(user=request.user)
    
    # Liczba produktów w lodówce
    item_count = fridge_items.count()
    
    # Liczba produktów przeterminowanych
    expired_count = fridge_items.filter(expiry_date__lt=date.today()).count()
    
    # Liczba produktów, które niedługo się przeterminują (w ciągu 3 dni)
    soon_expiring = fridge_items.filter(
        expiry_date__gte=date.today(),
        expiry_date__lte=date.today() + timedelta(days=3)
    ).count()
    
    # Pobierz produkty, które niedługo się przeterminują (w ciągu 7 dni)
    expiring_soon_items = fridge_items.filter(
        expiry_date__gte=date.today(),
        expiry_date__lte=date.today() + timedelta(days=7)
    ).select_related('ingredient', 'unit')[:10]  # Ogranicz do 10 produktów
    
    # Pobierz przepisy, które można przygotować z produktów w lodówce
    available_recipes = []
    recipes = Recipe.objects.filter(Q(author=request.user) | Q(is_public=True)).distinct()[:20]  # Ogranicz do 20 najnowszych przepisów
    
    for recipe in recipes:
        if recipe.can_be_prepared_with_available_ingredients(request.user):
            available_recipes.append({
                'recipe': recipe,
                'available': True,
            })
            if len(available_recipes) >= 5:  # Ogranicz do 5 przepisów
                break
    
    # Pobierz przepisy, które wykorzystują kończące się produkty
    expiring_ingredients = [item.ingredient for item in expiring_soon_items]
    recipes_with_expiring = []
    
    if expiring_ingredients:
        # Znajdź przepisy zawierające kończące się składniki
        recipes_with_expiring_ingredients = Recipe.objects.filter(
            Q(author=request.user) | Q(is_public=True),
            ingredients__ingredient__in=expiring_ingredients
        ).distinct()[:10]  # Ogranicz do 10 przepisów
        
        for recipe in recipes_with_expiring_ingredients:
            # Sprawdź, które z kończących się składników są używane w przepisie
            used_expiring = []
            for ingredient in expiring_ingredients:
                if recipe.ingredients.filter(ingredient=ingredient).exists():
                    # Znajdź odpowiedni FridgeItem, żeby pokazać ile dni zostało
                    expiring_item = next((item for item in expiring_soon_items if item.ingredient == ingredient), None)
                    if expiring_item:
                        used_expiring.append({
                            'name': ingredient.name,
                            'days_left': expiring_item.days_until_expiry,
                            'amount': expiring_item.amount,
                            'unit': expiring_item.unit.symbol
                        })
            
            if used_expiring:
                recipes_with_expiring.append({
                    'recipe': recipe,
                    'expiring_ingredients': used_expiring,
                    'can_be_prepared': recipe.can_be_prepared_with_available_ingredients(request.user)
                })
    
    context = {
        'item_count': item_count,
        'expired_count': expired_count,
        'soon_expiring': soon_expiring,
        'fridge_items': fridge_items, # Dodaję bezpośrednio wszystkie produkty
        'available_recipes': available_recipes,
        'expiring_soon_items': expiring_soon_items,
        'recipes_with_expiring': recipes_with_expiring
    }
    
    return render(request, 'fridge/dashboard.html', context)

class FridgeItemListView(LoginRequiredMixin, ListView):
    """Lista wszystkich produktów w lodówce"""
    model = FridgeItem
    template_name = 'fridge/fridge_list.html'
    context_object_name = 'fridge_items'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = FridgeItem.objects.filter(user=self.request.user)
        
        # Filtrowanie po wyszukiwanej frazie
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(ingredient__name__icontains=query) |
                Q(ingredient__category__name__icontains=query)
            )
        
        # Filtrowanie po statusie przeterminowania
        expired = self.request.GET.get('expired')
        today = date.today()
        
        if expired == 'yes':
            queryset = queryset.filter(expiry_date__lt=today)
        elif expired == 'no':
            queryset = queryset.filter(
                Q(expiry_date__gte=today) | Q(expiry_date__isnull=True)
            )
        elif expired == 'soon':
            queryset = queryset.filter(
                expiry_date__gte=today,
                expiry_date__lte=today + timedelta(days=7)
            )
        
        return queryset.order_by('expiry_date', 'ingredient__name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dodaj parametry filtrowania do kontekstu
        context['query'] = self.request.GET.get('q', '')
        context['expired'] = self.request.GET.get('expired', '')
        
        # Zlicz przeterminowane produkty
        context['expired_count'] = FridgeItem.objects.filter(
            user=self.request.user,
            expiry_date__lt=date.today()
        ).count()
        
        # Pobierz jednostki miary do legendy przeliczników
        context['measurement_units'] = self.get_measurement_units()
        
        # Konwertuj wszystkie produkty do jednostek podstawowych dla wyświetlania
        context['display_items'] = self.convert_to_base_units(context['fridge_items'])
        
        return context
    
    def convert_to_base_units(self, items):
        """
        Konwertuje wszystkie produkty do jednostek podstawowych (g/ml) dla wyświetlania.
        Nie zmienia oryginalnych danych w bazie.
        
        Returns:
            list: Lista słowników z przekonwertowanymi danymi
        """
        from recipes.utils import convert_units
        from recipes.models import MeasurementUnit
        
        # Pobierz podstawowe jednostki
        try:
            gram_unit = MeasurementUnit.objects.get(symbol='g')
            ml_unit = MeasurementUnit.objects.get(symbol='ml')
        except MeasurementUnit.DoesNotExist:
            # Jeśli nie ma podstawowych jednostek, zwróć oryginalne dane
            return list(items)
        
        display_items = []
        
        for item in items:
            # Kopiujemy wartości z oryginalnego obiektu
            display_item = {
                'id': item.id,
                'ingredient': item.ingredient,
                'amount': item.amount,
                'unit': item.unit,
                'expiry_date': item.expiry_date,
                'purchase_date': item.purchase_date,
                'is_expired': item.is_expired,
                'days_until_expiry': item.days_until_expiry,
                'original_amount': item.amount,  # zachowujemy oryginalną ilość
                'original_unit': item.unit,      # i oryginalną jednostkę
                'was_converted': False           # flaga czy była konwersja
            }
            
            # Określ jednostkę podstawową dla tego składnika
            if item.ingredient.unit_type.startswith('volume'):
                base_unit = ml_unit
            else:
                base_unit = gram_unit
            
            # Jeśli jednostka nie jest już podstawową, konwertuj
            if item.unit != base_unit:
                try:
                    # Konwertuj do jednostki podstawowej
                    converted_amount = convert_units(item.amount, item.unit, base_unit)
                    display_item['amount'] = converted_amount
                    display_item['unit'] = base_unit
                    display_item['was_converted'] = True
                except Exception as e:
                    # W przypadku błędu konwersji, zachowaj oryginalne wartości
                    print(f"Błąd konwersji dla {item.ingredient.name}: {str(e)}")
            
            display_items.append(display_item)
        
        return display_items
    
    def get_measurement_units(self):
        """
        Pobiera jednostki miary pogrupowane według typu do legendy przeliczników
        """
        units = {}
        
        # Pobierz popularne jednostki wagowe
        units['weight'] = MeasurementUnit.objects.filter(
            type='weight', 
            is_common=True
        ).order_by('base_ratio')
        
        # Pobierz popularne jednostki objętości
        units['volume'] = MeasurementUnit.objects.filter(
            type='volume', 
            is_common=True
        ).order_by('base_ratio')
        
        # Pobierz popularne jednostki łyżkowe
        units['spoon'] = MeasurementUnit.objects.filter(
            type='spoon', 
            is_common=True
        ).order_by('base_ratio')
        
        # Pobierz specjalne jednostki (szklanka, itp.)
        units['special'] = MeasurementUnit.objects.filter(
            description__icontains='szklanka'
        ).order_by('name')
        
        return units

class FridgeItemCreateView(LoginRequiredMixin, CreateView):
    """Dodawanie nowego produktu do lodówki"""
    model = FridgeItem
    form_class = FridgeItemForm
    template_name = 'fridge/fridge_wizard.html'
    success_url = reverse_lazy('fridge:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Pobierz dane z formularza
        ingredient = form.cleaned_data['ingredient']
        amount = form.cleaned_data['amount']
        unit = form.cleaned_data['unit']
        expiry_date = form.cleaned_data['expiry_date']
        
        # Zamiast zapisywać model bezpośrednio, użyj metody add_to_fridge
        try:
            item, was_converted = FridgeItem.add_to_fridge(
                user=self.request.user,
                ingredient=ingredient,
                amount=amount,
                unit=unit,
                expiry_date=expiry_date
            )
            
            # Wyświetl komunikat o sukcesie
            if was_converted:
                messages.success(
                    self.request,
                    f'Dodano {ingredient.name} w ilości {amount} {unit.symbol} '
                    f'(skonwertowano do {item.amount:.2f} {item.unit.symbol})'
                )
            else:
                messages.success(
                    self.request,
                    f'Dodano {ingredient.name} w ilości {amount} {unit.symbol}'
                )
            
            # Zaproponuj podobne produkty lub tablicę konwersji
            self.suggest_conversion_table(ingredient)
            
            return redirect(self.success_url)
        except ValueError as e:
            # W przypadku błędu dodaj go do formularza
            form.add_error(None, str(e))
            return self.form_invalid(form)
    
    def suggest_conversion_table(self, ingredient):
        """
        Sprawdza czy składnik ma zdefiniowane konwersje jednostek i sugeruje uzupełnienie
        tablicy konwersji, jeśli brakuje istotnych konwersji.
        """
        # Importuj modele konwersji
        from recipes.models import IngredientConversion, MeasurementUnit
        
        # Sprawdź czy składnik ma jakiekolwiek konwersje
        conversions = IngredientConversion.objects.filter(ingredient=ingredient)
        
        # Jeśli nie ma konwersji i mamy składnik z wieloma możliwymi jednostkami
        if not conversions.exists() and ingredient.unit_type not in ['weight_only', 'volume_only', 'piece_only']:
            # Sprawdź czy składnik ma określone podstawowe paramtery (gęstość, waga sztuki)
            missing_params = []
            
            # Sprawdź czy składnik może mieć konwersje między wagą a objętością
            if 'weight' in ingredient.unit_type and 'volume' in ingredient.unit_type and not ingredient.density:
                missing_params.append('gęstość (g/ml)')
            
            # Sprawdź czy składnik może mieć konwersje między wagą a sztukami
            if 'weight' in ingredient.unit_type and 'piece' in ingredient.unit_type and not ingredient.piece_weight:
                missing_params.append('wagę sztuki (g)')
            
            # Jeśli brakuje parametrów, wyświetl komunikat
            if missing_params:
                messages.warning(
                    self.request,
                    f'Aby umożliwić dokładniejsze konwersje jednostek dla {ingredient.name}, '
                    f'uzupełnij następujące parametry: {", ".join(missing_params)}.'
                )
            
            # Sugeruj utworzenie konwersji dla częstych jednostek
            messages.info(
                self.request,
                f'Ten składnik nie ma zdefiniowanej tablicy konwersji. '
                f'Możesz ją zdefiniować w panelu administracyjnym, '
                f'aby umożliwić dokładniejsze konwersje między różnymi jednostkami.'
            )

class FridgeItemUpdateView(LoginRequiredMixin, UpdateView):
    """Edycja produktu w lodówce"""
    model = FridgeItem
    form_class = FridgeItemForm
    template_name = 'fridge/fridge_form.html'
    success_url = reverse_lazy('fridge:list')
    
    def get_queryset(self):
        return FridgeItem.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Produkt w lodówce został zaktualizowany. Pamiętaj, że możesz zmieniać tylko ilość i datę ważności.')
        return super().form_valid(form)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            messages.info(self.request, 'Podczas edycji produktu możesz zmieniać tylko ilość i datę ważności. Składnik i jednostka nie mogą być zmienione.')
        return context

class FridgeItemDeleteView(LoginRequiredMixin, DeleteView):
    """Usuwanie produktu z lodówki"""
    model = FridgeItem
    template_name = 'fridge/fridge_confirm_delete.html'
    success_url = reverse_lazy('fridge:list')
    
    def get_queryset(self):
        return FridgeItem.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, f'Usunięto produkt z lodówki.')
        return super().delete(request, *args, **kwargs)

@login_required
def bulk_add_to_fridge(request):
    """Dodawanie wielu produktów naraz do lodówki"""
    if request.method == 'POST':
        try:
            # Pobierz dane JSON z formularza
            items_data = request.POST.get('items_data', '[]')
            
            # Dekoduj JSON
            items = json.loads(items_data)
            
            # Sprawdź czy lista nie jest pusta
            if not items:
                messages.warning(request, 'Nie dodano żadnych produktów. Formularz był pusty.')
                return redirect('fridge:bulk_add')
            
            # Liczniki dla statystyk
            added_count = 0
            converted_count = 0
            error_count = 0
            
            # Dodaj każdy produkt z listy
            for item in items:
                try:
                    ingredient_id = item.get('ingredient_id')
                    amount = item.get('amount')
                    unit_id = item.get('unit_id')
                    expiry_date = item.get('expiry_date') or None
                    
                    # Sprawdź czy wszystkie wymagane pola są dostępne
                    if not (ingredient_id and amount and unit_id):
                        continue
                    
                    # Pobierz obiekty z bazy danych
                    ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
                    unit = get_object_or_404(MeasurementUnit, pk=unit_id)
                    
                    # Przekonwertuj ilość na float
                    try:
                        amount = float(amount)
                    except (ValueError, TypeError):
                        # Jeśli nie da się przekonwertować, użyj wartości domyślnej 1
                        amount = 1
                    
                    # Dodaj produkt do lodówki - metoda add_to_fridge zajmie się konwersją
                    added_item, was_converted = FridgeItem.add_to_fridge(
                        user=request.user,
                        ingredient=ingredient,
                        amount=amount,
                        unit=unit,
                        expiry_date=expiry_date
                    )
                    
                    if was_converted:
                        converted_count += 1
                    
                    added_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"Błąd dodawania produktu: {str(e)}")
            
            # Wyświetl odpowiedni komunikat na podstawie liczników
            if added_count > 0:
                success_msg = f'Dodano {added_count} produktów do lodówki.'
                if converted_count > 0:
                    success_msg += f' {converted_count} produktów zostało skonwertowanych do jednostek podstawowych.'
                messages.success(request, success_msg)
            else:
                messages.warning(request, 'Nie udało się dodać żadnych produktów do lodówki.')
            
            if error_count > 0:
                messages.warning(request, f'Podczas dodawania wystąpiło {error_count} błędów.')
            
            return redirect('fridge:list')
        
        except json.JSONDecodeError:
            messages.error(request, 'Nieprawidłowy format danych. Spróbuj ponownie.')
        except Exception as e:
            messages.error(request, f'Wystąpił nieoczekiwany błąd: {str(e)}')
    
    # Renderuj pusty formularz dla żądania GET
    return render(request, 'fridge/bulk_add.html')

@login_required
def clean_expired(request):
    """Widok do usuwania przeterminowanych produktów"""
    # Pobierz wszystkie przeterminowane produkty
    expired_items = FridgeItem.objects.filter(
        user=request.user,
        expiry_date__lt=date.today()
    ).select_related('ingredient', 'unit')

    if request.method == 'POST':
        # Usuń przeterminowane produkty
        expired_items.delete()
        messages.success(request, 'Przeterminowane produkty zostały usunięte.')
        return redirect('fridge:list')

    # Przekaż listę przeterminowanych produktów do szablonu
    context = {
        'expired_items': expired_items,
    }
    return render(request, 'fridge/clean_expired_confirm.html', context)

@login_required
def available_recipes(request):
    """Pokazuje przepisy, które można przygotować z produktów w lodówce"""
    # Pobierz wszystkie przepisy użytkownika i publiczne przepisy
    recipes = Recipe.objects.filter(Q(author=request.user) | Q(is_public=True)).distinct()
    
    # Przygotuj listę przepisów z informacją o dostępności
    recipes_with_availability = []
    
    for recipe in recipes:
        # Sprawdź, czy wszystkie składniki są dostępne w odpowiedniej ilości
        can_be_prepared = recipe.can_be_prepared_with_available_ingredients(request.user)
        missing_ingredients = []
        
        if not can_be_prepared:
            # Jeśli nie wszystkie składniki są dostępne, zbierz listę brakujących
            missing_ingredients_data = recipe.get_missing_ingredients(request.user)
            if missing_ingredients_data:
                for item in missing_ingredients_data:
                    missing_ingredients.append({
                        'name': item.ingredient.name,
                        'amount': item.amount,
                        'unit': item.unit.symbol if item.unit else ''
                    })
        
        recipes_with_availability.append({
            'recipe': recipe,
            'available': can_be_prepared,
            'missing': missing_ingredients
        })
    
    return render(request, 'fridge/available_recipes.html', {
        'recipes': recipes_with_availability
    })

@login_required
def ajax_ingredient_search(request):
    """Widok do wyszukiwania składników przez AJAX"""
    term = request.GET.get('term', '')
    list_all = request.GET.get('list_all') == 'true'
    
    queryset = Ingredient.objects.all()
    if not list_all and term:
        queryset = queryset.filter(name__icontains=term)
    
    results = []
    for ingredient in queryset[:10]:  # Limit do 10 wyników
        results.append({
            'id': ingredient.id,
            'name': ingredient.name,
            'category': ingredient.category.name if ingredient.category else None
        })
    
    return JsonResponse({'results': results})

def ajax_load_units(request):
    """Widok do ładowania kompatybilnych jednostek dla wybranego składnika"""
    ingredient_id = request.GET.get('ingredient_id')
    units = []
    default_unit = None
    
    if ingredient_id:
        ingredient = get_object_or_404(Ingredient, id=ingredient_id)
        
        # Użyj metody get_allowed_units, która zwraca jednostki bazując na unit_type
        allowed_units = ingredient.get_allowed_units()
        
        # Ponadto, uwzględnij również jednostki explicite dodane jako kompatybilne
        compatible_units = ingredient.compatible_units.all()
        
        # Połącz obie listy jednostek (używamy distinct by uniknąć duplikatów)
        all_units = (allowed_units | compatible_units).distinct()
        
        # Jeśli nadal nie mamy żadnych jednostek, a istnieje domyślna - użyj jej
        if not all_units.exists() and ingredient.default_unit:
            all_units = [ingredient.default_unit]
            
        # Filtruj jednostki wagowe - zostaw tylko gramy i kilogramy (opcjonalnie)
        filtered_units = []
        for unit in all_units:
            if unit.type == 'weight':
                if unit.symbol in ['g', 'kg']:  # tylko gramy i kilogramy
                    filtered_units.append(unit)
            else:
                filtered_units.append(unit)
                
        # Jeśli nie mamy żadnych jednostek po filtrowaniu, użyj wszystkich
        if not filtered_units and all_units:
            filtered_units = list(all_units)
            
        units = [{
            'id': unit.id, 
            'name': unit.name, 
            'type': unit.type,
            'symbol': unit.symbol
        } for unit in filtered_units]
        
        default_unit = ingredient.default_unit.id if ingredient.default_unit else None
    
    return JsonResponse({
        'units': units,
        'default_unit': default_unit
    })

def ajax_compatible_units(request):
    """Funkcja AJAX do pobierania jednostek kompatybilnych z daną jednostką"""
    unit_id = request.GET.get('unit_id', '')
    
    if not unit_id.isdigit():
        return JsonResponse({'units': []})
    
    unit = get_object_or_404(MeasurementUnit, pk=unit_id)
    compatible_units = unit.get_compatible_units()
    
    return JsonResponse({
        'units': [{'id': u.id, 'name': u.name} for u in compatible_units]
    })

@login_required
def ajax_convert_units(request):
    """Widok AJAX do konwersji jednostek dla konkretnego składnika"""
    ingredient_id = request.GET.get('ingredient_id')
    amount = request.GET.get('amount')
    from_unit_id = request.GET.get('from_unit')
    to_unit_id = request.GET.get('to_unit')
    
    # Walidacja danych
    if not all([ingredient_id, amount, from_unit_id, to_unit_id]):
        return JsonResponse({'success': False, 'error': 'Brakujące parametry'})
    
    try:
        ingredient = get_object_or_404(Ingredient, id=ingredient_id)
        from_unit = get_object_or_404(MeasurementUnit, id=from_unit_id)
        to_unit = get_object_or_404(MeasurementUnit, id=to_unit_id)
        amount = float(amount)
        
        # Wykonaj konwersję
        from recipes.utils import convert_units
        converted_amount = convert_units(amount, from_unit, to_unit, ingredient=ingredient)
        
        # Sformatuj wynik z maksymalnie 4 miejscami po przecinku
        if converted_amount == int(converted_amount):
            # Jeśli liczba całkowita, usuń miejsca po przecinku
            formatted_amount = str(int(converted_amount))
        else:
            # W przeciwnym razie ogranicz liczbę miejsc po przecinku
            formatted_amount = '{:.4f}'.format(converted_amount).rstrip('0').rstrip('.')
        
        return JsonResponse({
            'success': True, 
            'converted_amount': formatted_amount,
            'from_unit': from_unit.symbol,
            'to_unit': to_unit.symbol
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def check_ingredient_availability(cls, user, ingredient, amount, unit):
    """
    Sprawdza, czy dany składnik jest dostępny w wystarczającej ilości.
    
    Args:
        user (User): Użytkownik
        ingredient (Ingredient): Składnik
        amount (float): Potrzebna ilość
        unit (MeasurementUnit): Jednostka
        
    Returns:
        bool: True jeśli składnik jest dostępny, False w przeciwnym razie
    """
    if not user or not user.is_authenticated:
        return False
    
    if amount <= 0:
        # Jeśli nie potrzebujemy składnika, to jest dostępny
        return True
    
    # Sprawdź czy jednostka jest określona
    if not unit:
        return False
    
    items = cls.objects.filter(
        user=user,
        ingredient=ingredient
    )
    
    if not items.exists():
        # Brak składnika w lodówce
        return False
    
    total_available = 0.0
    debug_info = []
    
    for item in items:
        try:
            # Jeśli jednostki są różne, przelicz ilość
            if item.unit != unit:
                try:
                    from recipes.utils import convert_units
                    converted_amount = convert_units(float(item.amount), item.unit, unit)
                    total_available += converted_amount
                    debug_info.append(f"Konwersja: {item.amount} {item.unit.symbol} -> {converted_amount} {unit.symbol}")
                except (ValueError, TypeError) as e:
                    # Logowanie błędu dla debugowania
                    debug_msg = f"Błąd konwersji: {e} dla {item.ingredient.name} z {item.unit} na {unit}"
                    print(debug_msg)
                    debug_info.append(debug_msg)
                    # Ignoruj ten produkt, jeśli konwersja nie jest możliwa
                    continue
            else:
                total_available += float(item.amount)
                debug_info.append(f"Bezpośrednio: {item.amount} {item.unit.symbol}")
        except Exception as e:
            # W przypadku nieoczekiwanego błędu, ignoruj ten produkt
            debug_msg = f"Nieoczekiwany błąd: {e}"
            print(debug_msg)
            debug_info.append(debug_msg)
            continue
    
    print(f"Dostępność składnika {ingredient.name}: potrzeba {amount} {unit.symbol}, dostępne {total_available} {unit.symbol}")
    print(f"Szczegóły konwersji: {', '.join(debug_info)}")
    
    # Porównanie dostępnej ilości z potrzebną ilością
    return total_available >= float(amount)

@login_required
def conversion_dashboard(request):
    """Panel zarządzania tablicami konwersji dla składników"""
    # Pobierz wszystkie składniki, które mają zdefiniowane konwersje
    ingredients_with_conversions = Ingredient.objects.filter(
        conversions__isnull=False
    ).distinct().order_by('name')
    
    # Pobierz składniki, które mogą mieć konwersje (z różnymi typami jednostek)
    ingredients_without_conversions = Ingredient.objects.filter(
        ~Q(unit_type__in=['weight_only', 'volume_only', 'piece_only']),
        ~Q(id__in=ingredients_with_conversions)
    ).order_by('name')
    
    # Pobierz najczęściej używane składniki z lodówki użytkownika
    from django.db.models import Count
    frequent_ingredients = FridgeItem.objects.filter(
        user=request.user
    ).values('ingredient__id', 'ingredient__name').annotate(
        count=Count('ingredient')
    ).order_by('-count')[:10]
    
    return render(request, 'fridge/conversion_dashboard.html', {
        'ingredients_with_conversions': ingredients_with_conversions,
        'ingredients_without_conversions': ingredients_without_conversions,
        'frequent_ingredients': frequent_ingredients
    })

@login_required
def ingredient_conversions(request, ingredient_id):
    """Wyświetla tablicę konwersji dla konkretnego składnika"""
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    
    # Pobierz wszystkie konwersje dla tego składnika
    conversions = IngredientConversion.objects.filter(ingredient=ingredient).order_by('from_unit__name', 'to_unit__name')
    
    # Pobierz dostępne jednostki dla tego składnika
    units = ingredient.get_allowed_units()
    
    # Sprawdź, jakie parametry są potrzebne do konwersji
    missing_params = []
    if 'weight' in ingredient.unit_type and 'volume' in ingredient.unit_type and not ingredient.density:
        missing_params.append({
            'name': 'density',
            'label': 'Gęstość (g/ml)',
            'description': 'Pozwala na konwersję między wagą a objętością'
        })
    
    if 'weight' in ingredient.unit_type and 'piece' in ingredient.unit_type and not ingredient.piece_weight:
        missing_params.append({
            'name': 'piece_weight',
            'label': 'Waga sztuki (g)',
            'description': 'Pozwala na konwersję między wagą a sztukami'
        })
    
    return render(request, 'fridge/ingredient_conversions.html', {
        'ingredient': ingredient,
        'conversions': conversions,
        'units': units,
        'missing_params': missing_params
    })

@login_required
def add_conversion(request, ingredient_id):
    """Dodaje nową konwersję dla składnika"""
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    
    if request.method == 'POST':
        from_unit_id = request.POST.get('from_unit')
        to_unit_id = request.POST.get('to_unit')
        ratio = request.POST.get('ratio')
        is_exact = request.POST.get('is_exact') == 'on'
        description = request.POST.get('description', '')
        
        # Walidacja danych
        errors = []
        if not from_unit_id:
            errors.append('Wybierz jednostkę źródłową')
        if not to_unit_id:
            errors.append('Wybierz jednostkę docelową')
        if not ratio:
            errors.append('Podaj współczynnik konwersji')
        else:
            try:
                ratio = float(ratio.replace(',', '.'))
                if ratio <= 0:
                    errors.append('Współczynnik musi być większy od zera')
            except ValueError:
                errors.append('Nieprawidłowy format współczynnika')
        
        if from_unit_id == to_unit_id:
            errors.append('Jednostki źródłowa i docelowa muszą być różne')
        
        # Jeśli są błędy, wyświetl je
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('fridge:add_conversion', ingredient_id=ingredient_id)
        
        # Pobierz jednostki
        from_unit = get_object_or_404(MeasurementUnit, id=from_unit_id)
        to_unit = get_object_or_404(MeasurementUnit, id=to_unit_id)
        
        # Sprawdź, czy konwersja już istnieje
        existing = IngredientConversion.objects.filter(
            ingredient=ingredient,
            from_unit=from_unit,
            to_unit=to_unit
        ).first()
        
        if existing:
            # Aktualizacja istniejącej konwersji
            existing.ratio = ratio
            existing.is_exact = is_exact
            existing.description = description
            existing.save()
            messages.success(request, f'Zaktualizowano konwersję dla {ingredient.name}')
        else:
            # Utworzenie nowej konwersji
            IngredientConversion.objects.create(
                ingredient=ingredient,
                from_unit=from_unit,
                to_unit=to_unit,
                ratio=ratio,
                is_exact=is_exact,
                description=description
            )
            messages.success(request, f'Dodano nową konwersję dla {ingredient.name}')
        
        # Sprawdź, czy dodać też odwrotną konwersję
        if request.POST.get('add_reverse') == 'on':
            # Oblicz odwrotny współczynnik
            reverse_ratio = 1 / ratio
            
            # Sprawdź, czy już istnieje
            existing_reverse = IngredientConversion.objects.filter(
                ingredient=ingredient,
                from_unit=to_unit,
                to_unit=from_unit
            ).first()
            
            if existing_reverse:
                existing_reverse.ratio = reverse_ratio
                existing_reverse.is_exact = is_exact
                existing_reverse.description = f"Odwrotność: {description}" if description else ""
                existing_reverse.save()
            else:
                IngredientConversion.objects.create(
                    ingredient=ingredient,
                    from_unit=to_unit,
                    to_unit=from_unit,
                    ratio=reverse_ratio,
                    is_exact=is_exact,
                    description=f"Odwrotność: {description}" if description else ""
                )
            
            messages.success(request, f'Dodano również odwrotną konwersję ({to_unit.symbol} → {from_unit.symbol})')
        
        return redirect('fridge:ingredient_conversions', ingredient_id=ingredient_id)
    
    # Pobierz dostępne jednostki dla tego składnika
    units = ingredient.get_allowed_units()
    
    return render(request, 'fridge/add_conversion.html', {
        'ingredient': ingredient,
        'units': units
    })

@login_required
def edit_conversion(request, conversion_id):
    """Edytuje istniejącą konwersję"""
    conversion = get_object_or_404(IngredientConversion, id=conversion_id)
    ingredient = conversion.ingredient
    
    if request.method == 'POST':
        ratio = request.POST.get('ratio')
        is_exact = request.POST.get('is_exact') == 'on'
        description = request.POST.get('description', '')
        
        # Walidacja danych
        errors = []
        if not ratio:
            errors.append('Podaj współczynnik konwersji')
        else:
            try:
                ratio = float(ratio.replace(',', '.'))
                if ratio <= 0:
                    errors.append('Współczynnik musi być większy od zera')
            except ValueError:
                errors.append('Nieprawidłowy format współczynnika')
        
        # Jeśli są błędy, wyświetl je
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('fridge:edit_conversion', conversion_id=conversion_id)
        
        # Aktualizacja konwersji
        conversion.ratio = ratio
        conversion.is_exact = is_exact
        conversion.description = description
        conversion.save()
        
        # Sprawdź, czy zaktualizować też odwrotną konwersję
        if request.POST.get('update_reverse') == 'on':
            # Sprawdź, czy istnieje odwrotna konwersja
            reverse_conversion = IngredientConversion.objects.filter(
                ingredient=ingredient,
                from_unit=conversion.to_unit,
                to_unit=conversion.from_unit
            ).first()
            
            if reverse_conversion:
                # Oblicz odwrotny współczynnik
                reverse_ratio = 1 / ratio
                reverse_conversion.ratio = reverse_ratio
                reverse_conversion.is_exact = is_exact
                reverse_conversion.save()
                messages.success(request, f'Zaktualizowano również odwrotną konwersję')
        
        messages.success(request, f'Zaktualizowano konwersję dla {ingredient.name}')
        return redirect('fridge:ingredient_conversions', ingredient_id=ingredient.id)
    
    return render(request, 'fridge/edit_conversion.html', {
        'conversion': conversion,
        'ingredient': ingredient
    })

@login_required
def delete_conversion(request, conversion_id):
    """Usuwa konwersję"""
    conversion = get_object_or_404(IngredientConversion, id=conversion_id)
    ingredient = conversion.ingredient
    
    if request.method == 'POST':
        # Sprawdź, czy usunąć też odwrotną konwersję
        if request.POST.get('delete_reverse') == 'on':
            # Sprawdź, czy istnieje odwrotna konwersja
            reverse_conversion = IngredientConversion.objects.filter(
                ingredient=ingredient,
                from_unit=conversion.to_unit,
                to_unit=conversion.from_unit
            ).first()
            
            if reverse_conversion:
                reverse_conversion.delete()
                messages.success(request, f'Usunięto również odwrotną konwersję')
        
        # Usuń konwersję
        conversion.delete()
        messages.success(request, f'Usunięto konwersję dla {ingredient.name}')
        return redirect('fridge:ingredient_conversions', ingredient_id=ingredient.id)
    
    return render(request, 'fridge/delete_conversion.html', {
        'conversion': conversion,
        'ingredient': ingredient
    })

@login_required
def update_ingredient_params(request, ingredient_id):
    """Aktualizuje parametry składnika (gęstość, waga sztuki)"""
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    
    if request.method == 'POST':
        density = request.POST.get('density')
        piece_weight = request.POST.get('piece_weight')
        
        # Aktualizuj parametry, jeśli podano
        if density:
            try:
                density = float(density.replace(',', '.'))
                if density > 0:
                    ingredient.density = density
            except ValueError:
                messages.error(request, 'Nieprawidłowy format gęstości')
        
        if piece_weight:
            try:
                piece_weight = float(piece_weight.replace(',', '.'))
                if piece_weight > 0:
                    ingredient.piece_weight = piece_weight
            except ValueError:
                messages.error(request, 'Nieprawidłowy format wagi sztuki')
        
        ingredient.save()
        messages.success(request, f'Zaktualizowano parametry dla {ingredient.name}')
        
        return redirect('fridge:ingredient_conversions', ingredient_id=ingredient_id)
    
    return render(request, 'fridge/update_params.html', {
        'ingredient': ingredient
    })

@login_required
def ajax_add_to_fridge(request):
    """Widok AJAX do dodawania produktu do lodówki"""
    if request.method == 'POST':
        try:
            # Pobierz dane z żądania
            ingredient_id = request.POST.get('ingredient')
            amount = request.POST.get('amount')
            unit_id = request.POST.get('unit')
            expiry_date = request.POST.get('expiry_date') or None
            
            # Sprawdź czy dane są kompletne
            if not ingredient_id or not amount or not unit_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Brakujące dane formularza. Wypełnij wszystkie wymagane pola.'
                })
            
            # Pobierz obiekty z bazy danych
            ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
            unit = get_object_or_404(MeasurementUnit, pk=unit_id)
            
            # Przekonwertuj amount na float
            try:
                amount = float(amount)
                if amount <= 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'Ilość musi być większa od zera.'
                    })
            except (ValueError, TypeError):
                return JsonResponse({
                    'success': False,
                    'error': 'Nieprawidłowa wartość ilości.'
                })
            
            # Dodaj produkt do lodówki
            try:
                item, was_converted = FridgeItem.add_to_fridge(
                    user=request.user,
                    ingredient=ingredient,
                    amount=amount,
                    unit=unit,
                    expiry_date=expiry_date
                )
                
                # Przygotuj komunikat
                if was_converted:
                    message = f'Dodano {ingredient.name} w ilości {amount} {unit.symbol} (skonwertowano do {item.amount:.2f} {item.unit.symbol})'
                else:
                    message = f'Dodano {ingredient.name} w ilości {amount} {unit.symbol}'
                
                # Dodaj komunikat do sesji, który zostanie wyświetlony po przekierowaniu
                messages.success(request, message)
                
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'redirect_url': reverse('fridge:list')
                })
            except ValueError as e:
                # Błąd konwersji jednostek
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            except Exception as e:
                # Inne nieoczekiwane błędy
                return JsonResponse({
                    'success': False,
                    'error': f'Nieoczekiwany błąd: {str(e)}'
                })
        except Exception as e:
            # Złap wszystkie inne błędy
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Nieoczekiwany błąd: {str(e)}'
            })
    
    # Jeśli nie POST, zwróć błąd
    return JsonResponse({
        'success': False,
        'error': 'Nieprawidłowe żądanie. Wymagane jest żądanie POST.'
    })

@login_required
def check_notifications(request):
    """
    Sprawdza czy są nowe powiadomienia o przeterminowaniu i generuje je.
    Powiadomienia są wyświetlane automatycznie na stronie, więc ten widok
    tylko je generuje i przekierowuje z powrotem.
    """
    # Generuj powiadomienia o przeterminowanych produktach
    notification_count = ExpiryNotification.check_expiring_products(request.user)
    
    if notification_count > 0:
        messages.info(request, f'Wygenerowano {notification_count} nowych powiadomień o produktach z kończącym się terminem ważności.')
    
    # Przekieruj z powrotem na stronę, z której przyszło żądanie
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        return redirect('fridge:list')

@login_required
def notifications_list(request):
    """Wyświetla listę powiadomień o przeterminowanych produktach"""
    # Pobierz powiadomienia dla zalogowanego użytkownika, posortowane od najnowszych
    notifications = ExpiryNotification.objects.filter(user=request.user).order_by('-created_at')
    
    # Zaktualizuj wszystkie nieprzeczytane powiadomienia jako przeczytane
    unread_notifications = notifications.filter(is_read=False)
    if unread_notifications.exists():
        unread_notifications.update(is_read=True)
    
    return render(request, 'fridge/notifications_list.html', {
        'notifications': notifications
    })

@login_required
def delete_notification(request, pk):
    """Usuwa pojedyncze powiadomienie"""
    notification = get_object_or_404(ExpiryNotification, pk=pk, user=request.user)
    notification.delete()
    messages.success(request, 'Powiadomienie zostało usunięte.')
    return redirect('fridge:notifications_list')

@login_required
def delete_all_notifications(request):
    """Usuwa wszystkie powiadomienia użytkownika"""
    if request.user.is_authenticated:
        ExpiryNotification.objects.filter(user=request.user).delete()
        messages.success(request, "Wszystkie powiadomienia zostały usunięte.")
    return redirect('fridge:notifications_list')

@login_required
def mark_notification_read(request, pk):
    """Oznacza pojedyncze powiadomienie jako przeczytane"""
    notification = get_object_or_404(ExpiryNotification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})

@login_required
def mark_all_notifications_read(request):
    """Oznacza wszystkie powiadomienia użytkownika jako przeczytane"""
    if request.user.is_authenticated:
        ExpiryNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, "Wszystkie powiadomienia zostały oznaczone jako przeczytane.")
    return redirect('fridge:notifications_list')