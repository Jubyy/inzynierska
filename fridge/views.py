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
    total_items = fridge_items.count()
    
    # Liczba produktów przeterminowanych
    expired_items = fridge_items.filter(expiry_date__lt=date.today()).count()
    
    # Liczba produktów, które niedługo się przeterminują (w ciągu 3 dni)
    soon_expiring = fridge_items.filter(
        expiry_date__gte=date.today(),
        expiry_date__lte=date.today() + timedelta(days=3)
    ).count()
    
    # Ostatnio dodane produkty (5 najnowszych)
    recent_items = fridge_items.order_by('-added_date')[:5]
    
    # Przepisy, które można przygotować z produktów w lodówce
    available_recipes_count = Recipe.objects.filter(user=request.user).count()
    
    context = {
        'total_items': total_items,
        'expired_items': expired_items,
        'soon_expiring': soon_expiring,
        'recent_items': recent_items,
        'available_recipes_count': available_recipes_count
    }
    
    return render(request, 'fridge/fridge_dashboard.html', context)

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
        
        return context

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
            FridgeItem.add_to_fridge(
                user=self.request.user,
                ingredient=form.cleaned_data['ingredient'],
                amount=form.cleaned_data['amount'],
                unit=form.cleaned_data['unit'],
                expiry_date=form.cleaned_data['expiry_date']
            )
            messages.success(self.request, 'Produkt został dodany do lodówki.')
            return JsonResponse({'success': True})
        except Exception as e:
            messages.error(self.request, f'Wystąpił błąd podczas dodawania produktu: {str(e)}')
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

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
        form = BulkAddForm(request.POST)
        
        if form.is_valid():
            items_data = request.POST.get('items_data', '[]')
            try:
                items = json.loads(items_data)
                
                for item in items:
                    ingredient_id = item.get('ingredient_id')
                    amount = item.get('amount')
                    unit_id = item.get('unit_id')
                    expiry_date = item.get('expiry_date') or None
                    
                    ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
                    unit = get_object_or_404(MeasurementUnit, pk=unit_id)
                    
                    FridgeItem.add_to_fridge(
                        user=request.user,
                        ingredient=ingredient,
                        amount=float(amount),
                        unit=unit,
                        expiry_date=expiry_date
                    )
                
                messages.success(request, f'Dodano {len(items)} produktów do lodówki.')
                return redirect('fridge:list')
            
            except Exception as e:
                messages.error(request, f'Wystąpił błąd podczas dodawania produktów: {str(e)}')
    else:
        form = BulkAddForm()
    
    return render(request, 'fridge/bulk_add.html', {
        'form': form,
    })

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
    # Pobierz wszystkie przepisy użytkownika
    recipes = Recipe.objects.filter(user=request.user)
    
    # Pobierz produkty z lodówki
    fridge_items = FridgeItem.objects.filter(user=request.user)
    
    # Przygotuj słownik dostępnych składników (id: [ilość, jednostka])
    available_ingredients = {}
    
    for item in fridge_items:
        if item.ingredient_id not in available_ingredients:
            available_ingredients[item.ingredient_id] = []
        
        available_ingredients[item.ingredient_id].append({
            'amount': item.amount,
            'unit': item.unit
        })
    
    # Sprawdź dla każdego przepisu, czy wszystkie składniki są dostępne
    recipes_with_availability = []
    
    for recipe in recipes:
        ingredients_needed = recipe.ingredients.all()
        
        # Sprawdź każdy składnik
        missing_ingredients = []
        all_available = True
        
        for ingredient_entry in ingredients_needed:
            ingredient_id = ingredient_entry.ingredient.id
            
            if ingredient_id not in available_ingredients:
                # Brak tego składnika w lodówce
                missing_ingredients.append(ingredient_entry.ingredient.name)
                all_available = False
                continue
            
            # TODO: W przyszłości można dodać sprawdzanie ilości i konwersji jednostek
        
        recipes_with_availability.append({
            'recipe': recipe,
            'available': all_available,
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
        # Pobierz kompatybilne jednostki dla składnika
        compatible_units = ingredient.compatible_units.all()
        
        # Jeśli nie ma kompatybilnych jednostek, użyj domyślnej jednostki
        if not compatible_units.exists() and ingredient.default_unit:
            compatible_units = [ingredient.default_unit]
        
        # Filtruj jednostki wagowe - zostaw tylko gramy i kilogramy
        filtered_units = []
        for unit in compatible_units:
            if unit.type == 'weight':
                if unit.symbol in ['g', 'kg']:  # tylko gramy i kilogramy
                    filtered_units.append(unit)
            else:
                filtered_units.append(unit)
            
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