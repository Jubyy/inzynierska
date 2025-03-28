from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q

from .models import ShoppingList, ShoppingItem
from recipes.models import Ingredient, MeasurementUnit, Recipe
from .forms import ShoppingListForm, ShoppingItemForm, ShoppingItemFormSet

class ShoppingListListView(LoginRequiredMixin, ListView):
    """Lista wszystkich list zakupów użytkownika"""
    model = ShoppingList
    template_name = 'shopping/shopping_list_list.html'
    context_object_name = 'shopping_lists'
    
    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_lists'] = self.get_queryset().filter(is_completed=False)
        context['completed_lists'] = self.get_queryset().filter(is_completed=True)
        return context

class ShoppingListDetailView(LoginRequiredMixin, DetailView):
    """Szczegółowy widok listy zakupów"""
    model = ShoppingList
    template_name = 'shopping/shopping_list_detail.html'
    context_object_name = 'shopping_list'
    
    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Podziel pozycje na zakupione i niezakupione
        context['unpurchased_items'] = self.object.items.filter(is_purchased=False)
        context['purchased_items'] = self.object.items.filter(is_purchased=True)
        
        # Przygotuj formularz do dodawania nowej pozycji
        context['form'] = ShoppingItemForm(initial={'shopping_list': self.object})
        
        return context

class ShoppingListCreateView(LoginRequiredMixin, CreateView):
    """Tworzenie nowej listy zakupów"""
    model = ShoppingList
    form_class = ShoppingListForm
    template_name = 'shopping/shopping_list_form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f'Lista zakupów "{form.instance.name}" została utworzona.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('shopping:detail', kwargs={'pk': self.object.pk})

class ShoppingListUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edycja listy zakupów"""
    model = ShoppingList
    form_class = ShoppingListForm
    template_name = 'shopping/shopping_list_form.html'
    
    def test_func(self):
        shopping_list = self.get_object()
        return self.request.user == shopping_list.user
    
    def form_valid(self, form):
        messages.success(self.request, f'Lista zakupów "{form.instance.name}" została zaktualizowana.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('shopping:detail', kwargs={'pk': self.object.pk})

class ShoppingListDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Usuwanie listy zakupów"""
    model = ShoppingList
    template_name = 'shopping/shopping_list_confirm_delete.html'
    success_url = reverse_lazy('shopping:list')
    
    def test_func(self):
        shopping_list = self.get_object()
        return self.request.user == shopping_list.user
    
    def delete(self, request, *args, **kwargs):
        shopping_list = self.get_object()
        messages.success(request, f'Lista zakupów "{shopping_list.name}" została usunięta.')
        return super().delete(request, *args, **kwargs)

@login_required
def add_shopping_item(request, pk):
    """Dodawanie pozycji do listy zakupów"""
    shopping_list = get_object_or_404(ShoppingList, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ShoppingItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.shopping_list = shopping_list
            item.save()
            
            messages.success(request, f'Dodano {item.ingredient.name} do listy zakupów.')
            return redirect('shopping:detail', pk=shopping_list.pk)
    else:
        form = ShoppingItemForm(initial={'shopping_list': shopping_list})
    
    return render(request, 'shopping/shopping_item_form.html', {'form': form, 'shopping_list': shopping_list})

@login_required
def edit_shopping_item(request, pk):
    """Edycja pozycji na liście zakupów"""
    item = get_object_or_404(ShoppingItem, pk=pk, shopping_list__user=request.user)
    shopping_list = item.shopping_list
    
    if request.method == 'POST':
        form = ShoppingItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            
            messages.success(request, f'Zaktualizowano {item.ingredient.name} na liście zakupów.')
            return redirect('shopping:detail', pk=shopping_list.pk)
    else:
        form = ShoppingItemForm(instance=item)
    
    return render(request, 'shopping/shopping_item_form.html', 
                 {'form': form, 'shopping_list': shopping_list, 'item': item})

@login_required
def delete_shopping_item(request, pk):
    """Usuwanie pozycji z listy zakupów"""
    item = get_object_or_404(ShoppingItem, pk=pk, shopping_list__user=request.user)
    shopping_list = item.shopping_list
    
    if request.method == 'POST':
        item_name = item.ingredient.name
        item.delete()
        
        messages.success(request, f'Usunięto {item_name} z listy zakupów.')
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    return render(request, 'shopping/shopping_item_confirm_delete.html', {'item': item})

@login_required
def toggle_purchased(request, pk):
    """Oznaczanie pozycji jako zakupionej/niezakupionej"""
    item = get_object_or_404(ShoppingItem, pk=pk, shopping_list__user=request.user)
    
    if request.method == 'POST':
        item.is_purchased = not item.is_purchased
        
        if item.is_purchased:
            item.mark_as_purchased()
            messages.success(request, f'Oznaczono {item.ingredient.name} jako zakupione.')
        else:
            item.is_purchased = False
            item.purchase_date = None
            item.save()
            messages.success(request, f'Oznaczono {item.ingredient.name} jako niezakupione.')
        
        return redirect('shopping:detail', pk=item.shopping_list.pk)
    
    return redirect('shopping:detail', pk=item.shopping_list.pk)

@login_required
def complete_shopping(request, pk):
    """Oznaczanie wszystkich pozycji na liście jako zakupione i dodawanie ich do lodówki"""
    shopping_list = get_object_or_404(ShoppingList, pk=pk, user=request.user)
    
    if request.method == 'POST':
        added_count = shopping_list.complete_shopping()
        
        if added_count > 0:
            messages.success(request, f'Zakończono zakupy! Dodano {added_count} produktów do lodówki.')
        else:
            messages.info(request, 'Lista zakupów została oznaczona jako zakończona.')
            
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    return render(request, 'shopping/complete_shopping.html', {'shopping_list': shopping_list})

@login_required
def create_from_recipe(request):
    """Tworzenie listy zakupów na podstawie przepisu"""
    if request.method == 'POST':
        recipe_id = request.POST.get('recipe')
        
        if recipe_id:
            recipe = get_object_or_404(Recipe, pk=recipe_id)
            
            # Utwórz nową listę zakupów
            list_name = f"Zakupy dla: {recipe.title}"
            shopping_list = ShoppingList.objects.create(user=request.user, name=list_name)
            
            # Dodaj składniki do listy
            created_items = shopping_list.add_recipe_ingredients(recipe)
            
            messages.success(request, f'Utworzono listę zakupów z {len(created_items)} składnikami dla przepisu "{recipe.title}".')
            return redirect('shopping:detail', pk=shopping_list.pk)
        else:
            messages.error(request, 'Wybierz przepis, aby utworzyć listę zakupów.')
    
    # Pobierz wszystkie przepisy
    recipes = Recipe.objects.all().order_by('title')
    
    return render(request, 'shopping/create_from_recipe.html', {'recipes': recipes})

def ajax_ingredient_search(request):
    """Wyszukiwanie składników za pomocą AJAX"""
    query = request.GET.get('term', '')
    if query:
        ingredients = Ingredient.objects.filter(name__icontains=query)[:10]
        results = [{'id': i.id, 'text': i.name} for i in ingredients]
    else:
        results = []
    
    return JsonResponse({'results': results})