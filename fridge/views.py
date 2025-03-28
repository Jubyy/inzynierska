from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q

from .models import FridgeItem
from recipes.models import Ingredient, MeasurementUnit, Recipe
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
        
        # Oznacz przeterminowane produkty
        for item in context['fridge_items']:
            item.expired = item.is_expired
            
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
    if query:
        ingredients = Ingredient.objects.filter(name__icontains=query)[:10]
        results = [{'id': i.id, 'text': i.name} for i in ingredients]
    else:
        results = []
    
    return JsonResponse({'results': results})