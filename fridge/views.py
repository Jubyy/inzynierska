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
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher

from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory
from .models import FridgeItem
from .forms import FridgeItemForm, BulkAddForm

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
                Q(notes__icontains=query)
            )
        
        # Filtrowanie po przeterminowaniu
        expired = self.request.GET.get('expired')
        if expired == 'yes':
            queryset = queryset.filter(expiry_date__lt=date.today())
        elif expired == 'no':
            queryset = queryset.filter(Q(expiry_date__gte=date.today()) | Q(expiry_date__isnull=True))
        
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
    template_name = 'fridge/fridge_form.html'
    success_url = reverse_lazy('fridge:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
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
    """Usuwa wszystkie przeterminowane produkty z lodówki"""
    if request.method == 'POST':
        expired_items = FridgeItem.objects.filter(
            user=request.user,
            expiry_date__lt=date.today()
        )
        
        count = expired_items.count()
        expired_items.delete()
        
        messages.success(request, f'Usunięto {count} przeterminowanych produktów.')
        return redirect('fridge:list')
    
    return render(request, 'fridge/clean_expired_confirm.html')

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

def ajax_ingredient_search(request):
    """Funkcja AJAX do wyszukiwania składników"""
    search_term = request.GET.get('term', '')
    
    if not search_term:
        return JsonResponse({'results': []})
    
    # Wyszukiwanie składników z nazwą zawierającą wyszukiwane hasło
    ingredients = Ingredient.objects.filter(name__icontains=search_term)[:10]
    
    results = []
    for ingredient in ingredients:
        default_unit = ingredient.default_unit
        unit_name = default_unit.name if default_unit else "brak"
        
        results.append({
            'id': ingredient.id,
            'text': f"{ingredient.name}",
            'name': ingredient.name,
            'category': ingredient.category.name if ingredient.category else "Inne",
            'unit': default_unit.id if default_unit else None,
            'unit_name': unit_name
        })
    
    # Dodaj opcję stworzenia nowego składnika
    if search_term:
        results.append({
            'id': 'new',
            'text': f"+ Dodaj nowy składnik: {search_term}",
            'name': search_term
        })
    
    return JsonResponse({'results': results})

def ajax_load_units(request):
    """Funkcja AJAX do pobierania jednostek miary dla składnika"""
    ingredient_id = request.GET.get('ingredient_id', '')
    
    if not ingredient_id.isdigit():
        # Zwracamy wszystkie jednostki, jeśli nie wybrano składnika lub wybrano nowy
        units = MeasurementUnit.objects.all()
    else:
        # Pobieramy jednostki kompatybilne z domyślną jednostką składnika
        ingredient = Ingredient.objects.get(id=ingredient_id)
        units = ingredient.compatible_units.all() if ingredient.compatible_units.exists() else MeasurementUnit.objects.all()
    
    return JsonResponse({
        'units': [{'id': unit.id, 'name': unit.name} for unit in units]
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