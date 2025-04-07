from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, FileResponse, HttpResponse
from django.db.models import Q, Sum
from django.template.loader import get_template
import io
from xhtml2pdf import pisa
from datetime import date

from .models import ShoppingList, ShoppingItem
from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory
from .forms import ShoppingListForm, ShoppingItemForm, ShoppingItemFormSet
from fridge.models import FridgeItem

class ShoppingListListView(LoginRequiredMixin, ListView):
    """Lista wszystkich list zakupów użytkownika"""
    model = ShoppingList
    template_name = 'shopping/shopping_list_list.html'
    context_object_name = 'shopping_lists'
    
    def get_queryset(self):
        try:
            return ShoppingList.objects.filter(user=self.request.user).order_by('-created_at')
        except Exception:
            # Obsługa przypadku, gdy tabela shopping_shoppinglist nie istnieje
            return ShoppingList.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['active_lists'] = self.get_queryset().filter(is_completed=False)
            context['completed_lists'] = self.get_queryset().filter(is_completed=True)
        except Exception:
            # Obsługa przypadku, gdy tabela shopping_shoppinglist nie istnieje
            context['active_lists'] = []
            context['completed_lists'] = []
            context['table_not_exists'] = True
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
        # Sprawdź czy to dodawanie wielu składników na raz
        if 'ingredient_ids[]' in request.POST:
            # Pobierz listę ID składników
            ingredient_ids = request.POST.getlist('ingredient_ids[]')
            amounts = request.POST.getlist('amounts[]')
            unit_ids = request.POST.getlist('unit_ids[]')
            
            added_count = 0
            errors = []
            
            for i, ingredient_id in enumerate(ingredient_ids):
                try:
                    ingredient = Ingredient.objects.get(pk=ingredient_id)
                    
                    # Sprawdź czy składnik jest już w liście
                    existing_item = ShoppingItem.objects.filter(
                        shopping_list=shopping_list,
                        ingredient=ingredient
                    ).first()
                    
                    if existing_item:
                        # Jeśli element już istnieje, zaktualizuj go
                        try:
                            amount = float(amounts[i])
                            unit = MeasurementUnit.objects.get(pk=unit_ids[i])
                            
                            if existing_item.unit == unit:
                                # Ta sama jednostka - po prostu dodaj wartość
                                existing_item.amount += amount
                                existing_item.save()
                            else:
                                # Różne jednostki - próba konwersji
                                try:
                                    # Skonwertuj nową wartość do jednostki istniejącego elementu
                                    from recipes.utils import convert_units
                                    converted_amount = convert_units(amount, unit, existing_item.unit)
                                    existing_item.amount += converted_amount
                                    existing_item.save()
                                except ValueError:
                                    # Jeśli nie można przekonwertować, dodaj jako nową pozycję
                                    ShoppingItem.objects.create(
                                        shopping_list=shopping_list,
                                        ingredient=ingredient,
                                        amount=amount,
                                        unit=unit
                                    )
                                    added_count += 1
                            
                        except (ValueError, IndexError):
                            errors.append(f"Błąd podczas aktualizacji {ingredient.name}")
                    else:
                        # Dodaj nowy składnik
                        try:
                            amount = float(amounts[i]) if i < len(amounts) else 1
                            unit = MeasurementUnit.objects.get(pk=unit_ids[i]) if i < len(unit_ids) else ingredient.default_unit
                            
                            ShoppingItem.objects.create(
                                shopping_list=shopping_list,
                                ingredient=ingredient,
                                amount=amount,
                                unit=unit
                            )
                            added_count += 1
                            
                        except (ValueError, IndexError, MeasurementUnit.DoesNotExist):
                            errors.append(f"Błąd podczas dodawania {ingredient.name}")
                    
                except Ingredient.DoesNotExist:
                    errors.append(f"Składnik o ID {ingredient_id} nie istnieje")
            
            if added_count > 0:
                messages.success(request, f'Dodano {added_count} składników do listy zakupów.')
            
            if errors:
                messages.warning(request, f'Wystąpiły błędy: {", ".join(errors)}')
            
            return redirect('shopping:detail', pk=shopping_list.pk)
        
        # Standardowe dodawanie pojedynczego składnika
        form = ShoppingItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.shopping_list = shopping_list
            
            # Sprawdź czy składnik już istnieje na liście
            existing_item = ShoppingItem.objects.filter(
                shopping_list=shopping_list,
                ingredient=item.ingredient
            ).first()
            
            if existing_item and existing_item.unit == item.unit:
                # Jeśli pozycja już istnieje z tą samą jednostką, zwiększ ilość
                existing_item.amount += item.amount
                existing_item.save()
                messages.success(request, f'Zaktualizowano ilość {item.ingredient.name} na liście zakupów.')
            else:
                # W przeciwnym razie zapisz nową pozycję
                item.save()
                messages.success(request, f'Dodano {item.ingredient.name} do listy zakupów.')
            
            return redirect('shopping:detail', pk=shopping_list.pk)
    else:
        form = ShoppingItemForm(initial={'shopping_list': shopping_list})
    
    # Pobierz wszystkie składniki i kategorie do formularza
    ingredients = Ingredient.objects.all().order_by('name')
    categories = IngredientCategory.objects.all().order_by('name')
    
    return render(request, 'shopping/shopping_item_form.html', {
        'form': form, 
        'shopping_list': shopping_list,
        'ingredients': ingredients,
        'categories': categories
    })

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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        # Jeśli produkt jest już zakupiony, nie robimy nic
        if item.is_purchased:
            if is_ajax:
                return JsonResponse({
                    'success': True, 
                    'purchased': True,
                    'message': f'Produkt {item.ingredient.name} jest już oznaczony jako zakupiony.'
                })
            messages.info(request, f'Produkt {item.ingredient.name} jest już oznaczony jako zakupiony.')
            return redirect('shopping:detail', pk=item.shopping_list.pk)
        
        # Oznacz jako zakupiony i dodaj do lodówki
        item.mark_as_purchased()
        
        # Sprawdź, czy wszystkie pozycje są już zakupione
        all_purchased = not item.shopping_list.items.filter(is_purchased=False).exists()
        has_recipe = item.shopping_list.recipe is not None
        recipe_id = item.shopping_list.recipe.id if has_recipe else None
        
        if is_ajax:
            return JsonResponse({
                'success': True, 
                'purchased': True,
                'all_purchased': all_purchased,
                'has_recipe': has_recipe,
                'recipe_id': recipe_id,
                'message': f'Oznaczono {item.ingredient.name} jako zakupione i dodano do lodówki.'
            })
        
        messages.success(request, f'Oznaczono {item.ingredient.name} jako zakupione i dodano do lodówki.')
        return redirect('shopping:detail', pk=item.shopping_list.pk)
    
    if is_ajax:
        return JsonResponse({'success': False, 'message': 'Niedozwolona metoda'}, status=405)
    return redirect('shopping:detail', pk=item.shopping_list.pk)

@login_required
def complete_shopping(request, pk):
    """Oznaczanie wszystkich pozycji na liście jako zakupione i dodawanie ich do lodówki"""
    shopping_list = get_object_or_404(ShoppingList, pk=pk, user=request.user)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Jeśli lista jest już zakończona, nie rób nic
    if shopping_list.is_completed:
        if is_ajax:
            return JsonResponse({
                'success': True,
                'completed': True,
                'message': 'Lista zakupów jest już zakończona.'
            })
        messages.info(request, 'Lista zakupów jest już zakończona.')
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    if request.method == 'POST':
        added_count = shopping_list.complete_shopping()
        
        # Sprawdź, czy lista ma powiązany przepis
        has_recipe = shopping_list.recipe is not None
        recipe_id = shopping_list.recipe.id if has_recipe else None
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'completed': True,
                'added_count': added_count,
                'has_recipe': has_recipe,
                'recipe_id': recipe_id,
                'message': f'Zakończono zakupy! Dodano {added_count} produktów do lodówki.'
            })
        
        if added_count > 0:
            messages.success(request, f'Zakończono zakupy! Dodano {added_count} produktów do lodówki.')
        else:
            messages.info(request, 'Lista zakupów została oznaczona jako zakończona.')
            
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    if is_ajax:
        return JsonResponse({
            'success': False, 
            'message': 'Ta operacja wymaga zapytania POST.'
        }, status=405)
        
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
            shopping_list = ShoppingList.objects.create(user=request.user, name=list_name, recipe=recipe)
            
            # Dodaj składniki do listy
            created_items = shopping_list.add_recipe_ingredients(recipe)
            
            messages.success(request, f'Utworzono listę zakupów z {len(created_items)} składnikami dla przepisu "{recipe.title}".')
            return redirect('shopping:detail', pk=shopping_list.pk)
        else:
            messages.error(request, 'Wybierz przepis, aby utworzyć listę zakupów.')
    
    # Pobierz wszystkie przepisy
    recipes = Recipe.objects.all().order_by('title')
    
    return render(request, 'shopping/create_from_recipe.html', {'recipes': recipes})

@login_required
def ajax_ingredient_search(request):
    """Widok AJAX do wyszukiwania składników z kategoriami"""
    term = request.GET.get('term', '')
    include_categories = request.GET.get('include_categories') == 'true'
    
    results = []
    
    if include_categories:
        # Pobierz wszystkie kategorie
        categories = IngredientCategory.objects.all().order_by('name')
        
        for category in categories:
            ingredients = Ingredient.objects.filter(
                category=category,
                name__icontains=term if term else ''
            ).order_by('name')
            
            if ingredients.exists():
                # Dodaj składniki z tej kategorii
                for ingredient in ingredients:
                    results.append({
                        'id': ingredient.id,
                        'text': ingredient.name,
                        'category': category.name
                    })
    else:
        # Proste wyszukiwanie bez kategorii
        ingredients = Ingredient.objects.filter(
            name__icontains=term
        ).order_by('name')[:10]
        
        results = [{'id': i.id, 'text': i.name} for i in ingredients]
    
    return JsonResponse({'results': results})

@login_required
def ajax_load_units(request):
    """Widok AJAX do ładowania jednostek dla wybranego składnika"""
    ingredient_id = request.GET.get('ingredient_id')
    
    if not ingredient_id:
        return JsonResponse({'units': [], 'default_unit': None})
    
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    compatible_units = ingredient.compatible_units.all()
    
    if not compatible_units.exists() and ingredient.default_unit:
        compatible_units = [ingredient.default_unit]
    
    units = [{'id': unit.id, 'name': unit.name, 'type': unit.type} for unit in compatible_units]
    default_unit = ingredient.default_unit.id if ingredient.default_unit else None
    
    return JsonResponse({
        'units': units,
        'default_unit': default_unit
    })

@login_required
def export_list_to_pdf(request, pk):
    """Eksportuje listę zakupów do pliku PDF używając xhtml2pdf, która obsługuje polskie znaki"""
    shopping_list = get_object_or_404(ShoppingList, pk=pk, user=request.user)
    
    # Przygotuj kontekst do szablonu
    context = {
        'shopping_list': shopping_list,
        'today': date.today(),
        'request': request,
        'items': shopping_list.items.all().order_by('ingredient__name'),
    }
    
    # Wygeneruj HTML z szablonu
    template = get_template('shopping/shopping_list_pdf.html')
    html = template.render(context)
    
    # Utwórz obiekt response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="lista_zakupow_{shopping_list.id}.pdf"'
    
    # Konwertuj HTML do PDF z obsługą polskich znaków
    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
        encoding='utf-8'
    )
    
    # Zwróć PDF jako odpowiedź
    if pisa_status.err:
        return HttpResponse('Wystąpił błąd podczas generowania PDF', status=500)
    return response