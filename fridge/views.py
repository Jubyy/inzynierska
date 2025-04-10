from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q
import json
import requests
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher

from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory
from .models import FridgeItem
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
    
    context = {
        'item_count': item_count,
        'expired_count': expired_count,
        'soon_expiring': soon_expiring,
        'fridge_items': fridge_items, # Dodaję bezpośrednio wszystkie produkty
        'available_recipes': available_recipes
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
        try:
            # Pobranie danych z formularza
            ingredient = form.cleaned_data['ingredient']
            unit = form.cleaned_data['unit']
            amount = form.cleaned_data['amount']
            expiry_date = form.cleaned_data['expiry_date']
            
            # Dodaj produkt do lodówki - metoda add_to_fridge zajmie się konwersją do jednostek podstawowych
            added_item, was_converted = FridgeItem.add_to_fridge(
                user=self.request.user,
                ingredient=ingredient,
                amount=amount,
                unit=unit,
                expiry_date=expiry_date
            )
            
            # Jeśli jednostka została zmieniona podczas dodawania, poinformuj użytkownika
            if was_converted:
                messages.info(
                    self.request, 
                    f'Produkt {ingredient.name} został dodany w jednostce {added_item.unit.name} '
                    f'(skonwertowano z {unit.name}) dla zachowania standardu podstawowych jednostek.'
                )
            else:
                messages.success(self.request, f'Produkt {ingredient.name} został dodany do lodówki.')
            
            return JsonResponse({'success': True})
        except ValueError as e:
            # Błąd walidacji (np. nieprawidłowa ilość)
            messages.error(self.request, f'Błąd walidacji: {str(e)}')
            return JsonResponse({'success': False, 'error': f'Błąd walidacji: {str(e)}'}, status=400)
        except Exception as e:
            # Inny nieoczekiwany błąd
            messages.error(self.request, f'Wystąpił nieoczekiwany błąd: {str(e)}')
            return JsonResponse({'success': False, 'error': f'Nieoczekiwany błąd: {str(e)}'}, status=500)

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
        return super().form_valid(form)

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

@classmethod
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
def consolidate_items(request):
    """Widok do konsolidacji produktów w lodówce do jednostek podstawowych"""
    if request.method == 'POST':
        try:
            # Wykonaj konsolidację
            consolidated_count = FridgeItem.consolidate_fridge_items(request.user)
            
            if consolidated_count > 0:
                messages.success(request, f'Skonsolidowano {consolidated_count} produktów w lodówce do jednostek podstawowych.')
            else:
                messages.info(request, 'Nie było potrzeby konsolidacji - wszystkie produkty są już w jednostkach podstawowych.')
                
        except Exception as e:
            messages.error(request, f'Wystąpił błąd podczas konsolidacji: {str(e)}')
            
        return redirect('fridge:list')
    
    # Pobierz produkty, które mogą być skonsolidowane (duplikaty składników)
    from django.db.models import Count
    
    duplicate_ingredients = FridgeItem.objects.filter(user=request.user).values(
        'ingredient__name'
    ).annotate(
        count=Count('ingredient')
    ).filter(count__gt=1).order_by('-count')
    
    ingredients_to_consolidate = []
    for item in duplicate_ingredients:
        ingredients_to_consolidate.append({
            'name': item['ingredient__name'],
            'count': item['count']
        })
    
    return render(request, 'fridge/consolidate_confirm.html', {
        'ingredients_to_consolidate': ingredients_to_consolidate
    })