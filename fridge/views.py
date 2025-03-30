from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q
import json
import requests
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory
from .models import FridgeItem
from .forms import FridgeItemForm, BulkAddForm

@login_required
def fridge_dashboard(request):
    """Główny widok lodówki z podsumowaniem produktów"""
    # Pobierz wszystkie produkty w lodówce użytkownika
    fridge_items = FridgeItem.objects.filter(user=request.user).order_by('ingredient__name')
    
    # Sprawdź przeterminowane produkty
    expired_items = [item for item in fridge_items if item.is_expired]
    
    # Pobierz przepisy, które można przygotować z dostępnych składników
    available_recipes = []
    recipes = Recipe.objects.all()
    
    for recipe in recipes:
        if recipe.can_be_prepared_with_available_ingredients(request.user):
            available_recipes.append(recipe)
    
    context = {
        'fridge_items': fridge_items,
        'expired_items': expired_items,
        'available_recipes': available_recipes[:5],  # Tylko 5 najnowszych przepisów
        'item_count': fridge_items.count(),
        'expired_count': len(expired_items)
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
        
        # Filtrowanie po składniku
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(ingredient__name__icontains=query)
            )
        
        # Sortowanie
        sort_by = self.request.GET.get('sort', 'ingredient__name')
        if sort_by == 'expiry':
            queryset = queryset.order_by('expiry_date', 'ingredient__name')
        else:
            queryset = queryset.order_by(sort_by)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['sort'] = self.request.GET.get('sort', 'ingredient__name')
        
        # Znajdź przeterminowane produkty
        expired_items = []
        for item in context['fridge_items']:
            item.expired = item.is_expired
            if item.is_expired:
                expired_items.append(item)
        
        context['expired_items'] = expired_items
        context['has_expired'] = len(expired_items) > 0
            
        return context

class FridgeItemCreateView(LoginRequiredMixin, CreateView):
    """Dodawanie nowego produktu do lodówki"""
    model = FridgeItem
    form_class = FridgeItemForm
    template_name = 'fridge/fridge_form.html'
    success_url = reverse_lazy('fridge:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Dodano {form.instance.ingredient.name} do lodówki.')
        return super().form_valid(form)

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
        messages.success(self.request, f'Zaktualizowano {form.instance.ingredient.name} w lodówce.')
        return super().form_valid(form)

class FridgeItemDeleteView(LoginRequiredMixin, DeleteView):
    """Usuwanie produktu z lodówki"""
    model = FridgeItem
    template_name = 'fridge/fridge_confirm_delete.html'
    success_url = reverse_lazy('fridge:list')
    
    def get_queryset(self):
        return FridgeItem.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        fridge_item = self.get_object()
        messages.success(request, f'Usunięto {fridge_item.ingredient.name} z lodówki.')
        return super().delete(request, *args, **kwargs)

@login_required
def bulk_add_to_fridge(request):
    """Dodawanie wielu produktów jednocześnie do lodówki"""
    if request.method == 'POST':
        form = BulkAddForm(request.POST)
        
        if form.is_valid():
            ingredients = request.POST.getlist('ingredients')
            amounts = request.POST.getlist('amounts')
            units = request.POST.getlist('units')
            expiry_dates = request.POST.getlist('expiry_dates')
            
            count = 0
            
            for i in range(len(ingredients)):
                if ingredients[i] and amounts[i] and units[i]:
                    ingredient = get_object_or_404(Ingredient, pk=ingredients[i])
                    unit = get_object_or_404(MeasurementUnit, pk=units[i])
                    amount = float(amounts[i])
                    expiry_date = expiry_dates[i] if expiry_dates[i] else None
                    
                    FridgeItem.add_to_fridge(
                        user=request.user,
                        ingredient=ingredient,
                        amount=amount,
                        unit=unit,
                        expiry_date=expiry_date
                    )
                    
                    count += 1
            
            messages.success(request, f'Dodano {count} produktów do lodówki.')
            return redirect('fridge:list')
    else:
        form = BulkAddForm()
    
    return render(request, 'fridge/bulk_add.html', {'form': form})

@login_required
def clean_expired(request):
    """Usuwanie przeterminowanych produktów z lodówki"""
    if request.method == 'POST':
        expired_items = [item for item in FridgeItem.objects.filter(user=request.user) if item.is_expired]
        count = len(expired_items)
        
        for item in expired_items:
            item.delete()
        
        messages.success(request, f'Usunięto {count} przeterminowanych produktów z lodówki.')
        return redirect('fridge:list')
    
    # Pobierz przeterminowane produkty
    expired_items = [item for item in FridgeItem.objects.filter(user=request.user) if item.is_expired]
    
    return render(request, 'fridge/clean_expired.html', {'expired_items': expired_items})

@login_required
def available_recipes(request):
    """Przepisy, które można przygotować z dostępnych składników"""
    recipes = Recipe.objects.all()
    available_recipes = []
    almost_available = []
    
    for recipe in recipes:
        missing = recipe.get_missing_ingredients(request.user)
        
        if not missing:
            available_recipes.append({'recipe': recipe, 'missing': []})
        elif len(missing) <= 3:  # Maksymalnie 3 brakujące składniki
            almost_available.append({'recipe': recipe, 'missing': missing})
    
    context = {
        'available_recipes': available_recipes,
        'almost_available': almost_available
    }
    
    return render(request, 'fridge/available_recipes.html', context)

def ajax_ingredient_search(request):
    """Wyszukiwanie składników za pomocą AJAX"""
    query = request.GET.get('term', '')
    include_categories = request.GET.get('include_categories', 'true') == 'true'
    
    if query:
        # Wyszukiwanie według zapytania
        ingredients = Ingredient.objects.filter(name__icontains=query).order_by('category__name', 'name')
        
        if include_categories:
            # Grupowanie według kategorii
            results = []
            categories = {}
            
            for ingredient in ingredients:
                category_name = ingredient.category.name
                if category_name not in categories:
                    categories[category_name] = {
                        'text': category_name,
                        'children': []
                    }
                
                categories[category_name]['children'].append({
                    'id': ingredient.id,
                    'text': ingredient.name
                })
            
            # Konwersja słownika kategorii na listę
            for category_name, category_data in categories.items():
                results.append(category_data)
        else:
            # Prosty format bez kategorii
            results = [{'id': i.id, 'text': i.name} for i in ingredients]
    else:
        # Gdy brak zapytania, zwróć pogrupowane składniki
        if include_categories:
            results = []
            categories = IngredientCategory.objects.all().order_by('name')
            
            for category in categories:
                # Pobierz wszystkie składniki z danej kategorii
                category_ingredients = Ingredient.objects.filter(category=category).order_by('name')
                if category_ingredients:
                    children = [{'id': i.id, 'text': i.name} for i in category_ingredients]
                    results.append({
                        'text': category.name,
                        'children': children
                    })
        else:
            # Zwróć wszystkie składniki alfabetycznie
            ingredients = Ingredient.objects.all().order_by('name')
            results = [{'id': i.id, 'text': i.name} for i in ingredients]
    
    return JsonResponse({'results': results})

def ajax_load_units(request):
    """Pobieranie jednostek miary za pomocą AJAX"""
    units = MeasurementUnit.objects.all()
    units_data = [{'id': u.id, 'name': u.name} for u in units]
    return JsonResponse({'units': units_data})

def ajax_compatible_units(request):
    """Pobieranie kompatybilnych jednostek miary dla składnika za pomocą AJAX"""
    ingredient_id = request.GET.get('ingredient_id')
    units = []
    default_unit = None
    
    if ingredient_id:
        ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
        
        # Najpierw pobierz kompatybilne jednostki
        compatible_units = ingredient.compatible_units.all()
        
        # Jeśli nie ma kompatybilnych jednostek, użyj wszystkich
        if not compatible_units.exists():
            units = MeasurementUnit.objects.all()
        else:
            units = compatible_units
            
        # Sprawdź, czy jest domyślna jednostka
        default_unit = ingredient.default_unit.id if ingredient.default_unit else None
    else:
        # Jeśli nie podano składnika, zwróć wszystkie jednostki
        units = MeasurementUnit.objects.all()
    
    units_data = [{'id': u.id, 'name': u.name} for u in units]
    return JsonResponse({'units': units_data, 'default_unit': default_unit})

@login_required
def barcode_scan(request):
    """Widok do skanowania kodów kreskowych produktów"""
    return render(request, 'fridge/barcode_scan.html')

def ajax_barcode_lookup(request):
    """
    Wyszukiwanie informacji o produkcie na podstawie kodu kreskowego.
    W tym przykładzie używamy Open Food Facts API do pobierania danych o produktach.
    """
    barcode = request.GET.get('barcode', '').strip()
    
    if not barcode:
        return JsonResponse({
            'success': False,
            'error': 'Nie podano kodu kreskowego'
        })
    
    try:
        # Najpierw sprawdź, czy mamy już taki produkt w bazie
        ingredient = Ingredient.objects.filter(barcode=barcode).first()
        
        # Jeśli produkt nie istnieje z takim kodem, ale może być tylko numerem ID
        if not ingredient and barcode.isdigit():
            ingredient = Ingredient.objects.filter(id=barcode).first()
        
        if ingredient:
            # Jeśli produkt istnieje w bazie, zwróć jego dane
            return JsonResponse({
                'success': True,
                'exists': True,
                'product': {
                    'id': ingredient.id,
                    'name': ingredient.name,
                    'unit': ingredient.default_unit.id if ingredient.default_unit else None,
                    'unit_name': ingredient.default_unit.name if ingredient.default_unit else None,
                }
            })
        
        # Jeśli produktu nie ma w bazie, spróbuj pobrać dane z Open Food Facts
        # Spróbuj najpierw z polskiej wersji API
        apis_to_try = [
            f'https://pl.openfoodfacts.org/api/v0/product/{barcode}.json',
            f'https://world.openfoodfacts.org/api/v0/product/{barcode}.json'
        ]
        
        product_found = False
        product_data = {}
        
        for api_url in apis_to_try:
            try:
                response = requests.get(api_url, timeout=7)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 1:
                        product_data = data.get('product', {})
                        product_found = True
                        break
            except Exception as e:
                print(f"Błąd podczas próby pobierania z {api_url}: {str(e)}")
                continue
        
        if product_found:
            # Pobieranie nazwy produktu z różnych pól (w zależności od dostępności)
            product_name = (
                product_data.get('product_name_pl') or 
                product_data.get('product_name') or 
                product_data.get('generic_name_pl') or
                product_data.get('generic_name') or
                product_data.get('abbreviated_product_name') or
                ''
            )
            
            if not product_name:
                return JsonResponse({
                    'success': False,
                    'error': 'Nie znaleziono nazwy produktu'
                })
            
            # Szukamy podobnych składników w bazie danych
            similar_ingredients = []
            all_ingredients = Ingredient.objects.all()
            
            # Funkcja do obliczania podobieństwa nazw
            def similarity_ratio(a, b):
                return SequenceMatcher(None, a.lower(), b.lower()).ratio()
            
            # Filtrowanie składników o podobnych nazwach
            for db_ingredient in all_ingredients:
                # Główne podobieństwo nazwy
                similarity = similarity_ratio(product_name, db_ingredient.name)
                
                # Sprawdzamy, czy produkt jest podobny do istniejącego składnika
                if similarity > 0.6:  # 60% podobieństwa
                    similar_ingredients.append({
                        'id': db_ingredient.id,
                        'name': db_ingredient.name,
                        'similarity': similarity,
                        'unit': db_ingredient.default_unit.id if db_ingredient.default_unit else None,
                        'unit_name': db_ingredient.default_unit.name if db_ingredient.default_unit else None,
                    })
            
            # Sortuj podobne składniki według podobieństwa (od najwyższego)
            similar_ingredients = sorted(similar_ingredients, key=lambda x: x['similarity'], reverse=True)
            
            # Przygotuj dane dotyczące ilości
            quantity = product_data.get('quantity', '')
            
            # Przygotuj dane dotyczące kategorii
            categories = (
                product_data.get('categories_tags', []) or 
                product_data.get('categories_hierarchy', []) or
                []
            )
            
            categories_display = ', '.join([c.replace('en:', '').replace('pl:', '').replace('-', ' ') for c in categories[:3]]) if categories else ''
            
            # Pobierz obraz produktu (wybierz najlepsze dostępne zdjęcie)
            image_url = (
                product_data.get('image_front_url') or 
                product_data.get('image_front_small_url') or
                product_data.get('image_url') or
                product_data.get('image_small_url') or
                ''
            )
            
            # Zwracamy dane do formularza
            return JsonResponse({
                'success': True,
                'exists': False,
                'product': {
                    'name': product_name,
                    'quantity': quantity,
                    'image_url': image_url,
                    'categories': categories_display,
                    'barcode': barcode
                },
                'similar_ingredients': similar_ingredients[:5]  # Ograniczamy do 5 najlepszych wyników
            })
        else:
            # Jeśli nie znaleziono w Open Food Facts, próbujemy utworzyć przykładowy produkt
            sample_name = f"Produkt {barcode[:4]}-{barcode[-4:]}"
            return JsonResponse({
                'success': True,
                'exists': False,
                'product': {
                    'name': sample_name,
                    'quantity': '',
                    'image_url': '',
                    'categories': '',
                    'barcode': barcode
                },
                'similar_ingredients': []
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Wystąpił błąd podczas wyszukiwania: {str(e)}'
        })

@login_required
def add_scanned_product(request):
    """Dodawanie produktu zeskanowanego lub wyszukanego po kodzie kreskowym"""
    if request.method == 'POST':
        try:
            # Pobierz dane z formularza
            product_name = request.POST.get('ingredient')
            amount = float(request.POST.get('amount'))
            unit_id = request.POST.get('unit')
            expiry_date = request.POST.get('expiry_date') or None
            barcode = request.POST.get('barcode')
            
            # Pobierz lub utwórz składnik
            unit = get_object_or_404(MeasurementUnit, pk=unit_id)
            
            # Sprawdź, czy składnik istnieje w bazie
            ingredient = Ingredient.objects.filter(name=product_name).first()
            
            if not ingredient:
                # Jeśli składnik nie istnieje, utwórz nowy
                # Najpierw pobierz kategorię domyślną
                default_category = IngredientCategory.objects.first()
                if not default_category:
                    # Jeśli nie ma kategorii, utwórz domyślną
                    default_category = IngredientCategory.objects.create(
                        name="Inne", 
                        is_vegetarian=True,
                        is_vegan=False
                    )
                
                # Utwórz nowy składnik
                ingredient = Ingredient.objects.create(
                    name=product_name,
                    category=default_category,
                    barcode=barcode if barcode != product_name else None,
                    default_unit=unit
                )
            
            # Dodaj produkt do lodówki
            FridgeItem.add_to_fridge(
                user=request.user,
                ingredient=ingredient,
                amount=amount,
                unit=unit,
                expiry_date=expiry_date
            )
            
            messages.success(request, f'Dodano {product_name} do lodówki.')
            return JsonResponse({'success': True, 'redirect': reverse('fridge:list')})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Nieprawidłowe żądanie'})