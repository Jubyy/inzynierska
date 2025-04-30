from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, FileResponse, HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.db.models import Q, Sum
from django.template.loader import get_template
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
import io
from xhtml2pdf import pisa
from datetime import date
import tempfile
import os
import subprocess
from django.template.loader import render_to_string
import logging
from io import BytesIO
try:
    import pdfkit
except ImportError:
    pdfkit = None

from .models import ShoppingList, ShoppingItem
from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory
from .forms import ShoppingListForm, ShoppingItemForm, ShoppingItemFormSet
from fridge.models import FridgeItem

logger = logging.getLogger(__name__)

# Próbujemy zaimportować WeasyPrint, ale obsługujemy przypadek, gdy nie jest dostępny
try:
    from weasyprint import HTML, CSS
    from weasyprint.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint nie jest dostępny. Funkcja generowania PDF będzie ograniczona.")

class ShoppingListListView(LoginRequiredMixin, ListView):
    """Lista wszystkich list zakupów użytkownika"""
    model = ShoppingList
    template_name = 'shopping/shopping_list_list.html'
    context_object_name = 'shopping_lists'
    
    def get_queryset(self):
        try:
            queryset = ShoppingList.objects.filter(user=self.request.user)
            
            # Filtrowanie po statusie
            status = self.request.GET.get('status')
            if status == 'active':
                queryset = queryset.filter(is_completed=False)
            elif status == 'completed':
                queryset = queryset.filter(is_completed=True)
                
            # Wyszukiwanie po nazwie
            search = self.request.GET.get('search')
            if search:
                queryset = queryset.filter(name__icontains=search)
                
            # Sortowanie
            sort_by = self.request.GET.get('sort_by', 'created_at')
            sort_order = self.request.GET.get('sort_order', 'desc')
            
            order_prefix = '-' if sort_order == 'desc' else ''
            order_field = {
                'name': 'name',
                'created_at': 'created_at',
                'modified_at': 'modified_at',
                'item_count': 'items__count'
            }.get(sort_by, 'created_at')
            
            # Specjalne sortowanie dla ilości produktów
            if sort_by == 'item_count':
                from django.db.models import Count
                queryset = queryset.annotate(items__count=Count('items'))
                
            queryset = queryset.order_by(f"{order_prefix}{order_field}")
            
            return queryset
        except Exception as e:
            # Obsługa przypadku, gdy tabela shopping_shoppinglist nie istnieje
            print(f"Błąd podczas pobierania list zakupów: {str(e)}")
            return ShoppingList.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            queryset = self.get_queryset()
            context['active_lists'] = queryset.filter(is_completed=False)
            context['completed_lists'] = queryset.filter(is_completed=True)
            
            # Dodaj parametry filtrowania i sortowania do kontekstu
            context['status'] = self.request.GET.get('status', '')
            context['search'] = self.request.GET.get('search', '')
            context['sort_by'] = self.request.GET.get('sort_by', 'created_at')
            context['sort_order'] = self.request.GET.get('sort_order', 'desc')
            
            # Liczniki dla statystyk
            context['total_count'] = queryset.count()
            context['active_count'] = context['active_lists'].count()
            context['completed_count'] = context['completed_lists'].count()
            
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
        
        # Filtry i sortowanie dla pozycji na liście
        search = self.request.GET.get('search', '')
        category = self.request.GET.get('category', '')
        sort_by = self.request.GET.get('sort_by', 'ingredient__name')
        sort_order = self.request.GET.get('sort_order', 'asc')
        view_mode = self.request.GET.get('view_mode', 'list')  # 'list' lub 'category'
        
        # Bazowy queryset dla niezakupionych i zakupionych pozycji
        unpurchased_items = self.object.items.filter(is_purchased=False)
        purchased_items = self.object.items.filter(is_purchased=True)
        
        # Zastosuj filtrowanie
        if search:
            unpurchased_items = unpurchased_items.filter(
                Q(ingredient__name__icontains=search) |
                Q(note__icontains=search)
            )
            purchased_items = purchased_items.filter(
                Q(ingredient__name__icontains=search) |
                Q(note__icontains=search)
            )
        
        if category:
            unpurchased_items = unpurchased_items.filter(ingredient__category__name=category)
            purchased_items = purchased_items.filter(ingredient__category__name=category)
        
        # Zastosuj sortowanie
        order_prefix = '-' if sort_order == 'desc' else ''
        order_field = {
            'ingredient__name': 'ingredient__name',
            'amount': 'amount',
            'unit__name': 'unit__name',
            'purchase_date': 'purchase_date',
            'note': 'note'
        }.get(sort_by, 'ingredient__name')
        
        unpurchased_items = unpurchased_items.order_by(f"{order_prefix}{order_field}")
        purchased_items = purchased_items.order_by(f"{order_prefix}{order_field}")
        
        # Pobierz kategorie składników do filtrowania
        categories = IngredientCategory.objects.all().order_by('name')
        
        # W zależności od trybu widoku, zapewniamy różne dane
        if view_mode == 'category':
            # Grupuj według kategorii
            context['unpurchased_by_category'] = self.object.get_unpurchased_items_by_category()
            context['purchased_by_category'] = self.object.get_purchased_items_by_category()
        
        # Podziel pozycje na zakupione i niezakupione
        context['unpurchased_items'] = unpurchased_items
        context['purchased_items'] = purchased_items
        
        # Dodaj opcje filtrowania i sortowania
        context['search'] = search
        context['selected_category'] = category
        context['categories'] = categories
        context['sort_by'] = sort_by
        context['sort_order'] = sort_order
        context['view_mode'] = view_mode
        
        # Dodaj statystyki
        context['total_items'] = self.object.items.count()
        context['purchased_count'] = purchased_items.count()
        context['unpurchased_count'] = unpurchased_items.count()
        
        if context['total_items'] > 0:
            context['purchase_percentage'] = int((context['purchased_count'] / context['total_items']) * 100)
        else:
            context['purchase_percentage'] = 0
        
        # Przygotuj formularz do dodawania nowej pozycji
        context['form'] = ShoppingItemForm(initial={'shopping_list': self.object})
        
        # Sprawdź czy istnieją duplikaty składników, które można skonsolidować
        from django.db.models import Count
        duplicate_ingredients = self.object.items.values('ingredient_id').annotate(
            count=Count('ingredient_id')
        ).filter(count__gt=1)
        context['has_duplicates'] = duplicate_ingredients.exists()
        
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
            
            print(f"Otrzymane dane: {len(ingredient_ids)} składników, {len(amounts)} ilości, {len(unit_ids)} jednostek")
            
            if not ingredient_ids:
                messages.error(request, "Nie wybrano żadnych składników do dodania.")
                return redirect('shopping:detail', pk=shopping_list.pk)
            
            for i, ingredient_id in enumerate(ingredient_ids):
                try:
                    ingredient = Ingredient.objects.get(pk=ingredient_id)
                    
                    # Pobierz jednostkę
                    try:
                        unit_id = unit_ids[i] if i < len(unit_ids) else None
                        if unit_id and unit_id != 'null':
                            unit = MeasurementUnit.objects.get(pk=unit_id)
                        else:
                            # Jeśli brak jednostki, użyj domyślnej dla składnika
                            unit = ingredient.default_unit
                            if not unit:
                                # Jeśli nadal brak, użyj pierwszej kompatybilnej jednostki
                                compatible_units = ingredient.compatible_units.all()
                                if compatible_units.exists():
                                    unit = compatible_units.first()
                                else:
                                    # Ostatecznie użyj podstawowej jednostki (g)
                                    unit = MeasurementUnit.objects.filter(symbol='g').first()
                                    if not unit:
                                        # Jeśli nawet brak podstawowej jednostki, użyj dowolnej pierwszej
                                        unit = MeasurementUnit.objects.first()
                                        if not unit:
                                            # Jeśli nie ma żadnej jednostki, zgłoś błąd
                                            raise MeasurementUnit.DoesNotExist("Brak dostępnych jednostek miary!")
                    except (MeasurementUnit.DoesNotExist, ValueError) as e:
                        errors.append(f"Brak jednostki dla składnika {ingredient.name}: {str(e)}")
                        continue
                    
                    # Pobierz ilość
                    try:
                        amount = float(amounts[i]) if i < len(amounts) else 1.0
                    except (ValueError, IndexError) as e:
                        amount = 1.0  # Domyślna ilość w przypadku błędu
                    
                    # Sprawdź czy składnik jest już w liście
                    existing_item = ShoppingItem.objects.filter(
                        shopping_list=shopping_list,
                        ingredient=ingredient
                    ).first()
                    
                    if existing_item:
                        # Jeśli element już istnieje, zaktualizuj go
                        if existing_item.unit == unit:
                            # Ta sama jednostka - po prostu dodaj wartość
                            existing_item.amount += amount
                            existing_item.save()
                            added_count += 1
                        else:
                            # Różne jednostki - próba konwersji
                            try:
                                # Skonwertuj nową wartość do jednostki istniejącego elementu
                                from recipes.utils import convert_units
                                converted_amount = convert_units(amount, unit, existing_item.unit, ingredient=ingredient)
                                existing_item.amount += converted_amount
                                existing_item.save()
                                added_count += 1
                            except ValueError:
                                # Jeśli nie można przekonwertować, dodaj jako nową pozycję
                                ShoppingItem.objects.create(
                                    shopping_list=shopping_list,
                                    ingredient=ingredient,
                                    amount=amount,
                                    unit=unit
                                )
                                added_count += 1
                    else:
                        # Dodaj nowy składnik
                        ShoppingItem.objects.create(
                            shopping_list=shopping_list,
                            ingredient=ingredient,
                            amount=amount,
                            unit=unit
                        )
                        added_count += 1
                    
                except Ingredient.DoesNotExist:
                    errors.append(f"Składnik o ID {ingredient_id} nie istnieje")
                except Exception as e:
                    errors.append(f"Błąd dla składnika {ingredient_id}: {str(e)}")
            
            if added_count > 0:
                messages.success(request, f'Dodano {added_count} składników do listy zakupów.')
            else:
                messages.warning(request, f'Nie udało się dodać żadnych składników do listy.')
            
            if errors:
                messages.warning(request, f'Wystąpiły błędy: {", ".join(errors[:5])}' + ("..." if len(errors) > 5 else ""))
            
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
            
            if existing_item:
                if existing_item.unit == item.unit:
                    # Jeśli pozycja już istnieje z tą samą jednostką, zwiększ ilość
                    existing_item.amount += item.amount
                    existing_item.save()
                    messages.success(request, f'Zaktualizowano ilość {item.ingredient.name} na liście zakupów.')
                else:
                    # Różne jednostki - spróbuj konwersji
                    try:
                        # Skonwertuj nową wartość do jednostki istniejącego elementu
                        from recipes.utils import convert_units
                        converted_amount = convert_units(item.amount, item.unit, existing_item.unit, ingredient=item.ingredient)
                        existing_item.amount += converted_amount
                        existing_item.save()
                        messages.success(request, f'Zaktualizowano ilość {item.ingredient.name} na liście zakupów (po konwersji jednostek).')
                    except ValueError:
                        # Jeśli nie można przekonwertować, dodaj jako nową pozycję
                        item.save()
                        messages.success(request, f'Dodano {item.ingredient.name} z nową jednostką do listy zakupów.')
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
        # Inicjalizacja formularza z ukrytymi polami zawierającymi oryginalne wartości
        form = ShoppingItemForm(
            instance=item, 
            initial={
                'hidden_ingredient': item.ingredient.id,
                'hidden_unit': item.unit.id
            }
        )
    
    # Pobierz wszystkie składniki i kategorie do formularza
    ingredients = Ingredient.objects.all().order_by('name')
    categories = IngredientCategory.objects.all().order_by('name')
    
    return render(request, 'shopping/shopping_item_form.html', {
        'form': form, 
        'shopping_list': shopping_list, 
        'item': item,
        'ingredients': ingredients,
        'categories': categories
    })

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
        success = item.mark_as_purchased()
        
        # Sprawdź, czy wszystkie pozycje są już zakupione
        all_purchased = not item.shopping_list.items.filter(is_purchased=False).exists()
        if all_purchased:
            # Oznacz listę jako zakończoną
            item.shopping_list.is_completed = True
            item.shopping_list.save()
            
        has_recipe = item.shopping_list.recipe is not None
        recipe_id = item.shopping_list.recipe.id if has_recipe else None
        
        if is_ajax:
            return JsonResponse({
                'success': success, 
                'purchased': True,
                'all_purchased': all_purchased,
                'has_recipe': has_recipe,
                'recipe_id': recipe_id,
                'message': f'Oznaczono {item.ingredient.name} jako zakupione i dodano do lodówki.'
            })
        
        if success:
            messages.success(request, f'Oznaczono {item.ingredient.name} jako zakupione i dodano do lodówki.')
        else:
            messages.warning(request, f'Oznaczono {item.ingredient.name} jako zakupione, ale nie udało się dodać do lodówki.')
            
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
    """Export shopping list to PDF przy uzyciu reportlab."""
    logger.info(f"Eksportowanie listy zakupow o id {pk} do PDF")
    
    # Sprawdź, czy WeasyPrint jest dostępny
    if not 'reportlab' in globals():
        messages.warning(request, "Generowanie PDF jest niedostępne. Brak wymaganych bibliotek.")
        return redirect('shopping:detail', pk=pk)
    
    try:
        # Pobierz liste zakupow
        shopping_list = get_object_or_404(ShoppingList, pk=pk, user=request.user)
        
        # Pobierz produkty z listy zakupow
        items = ShoppingItem.objects.filter(shopping_list=shopping_list).select_related('ingredient', 'unit', 'ingredient__category')
        
        # Grupuj produkty wedlug kategorii
        products_by_category = {}
        for item in items:
            category_name = item.ingredient.category.name if item.ingredient and item.ingredient.category else "Inne"
            if category_name not in products_by_category:
                products_by_category[category_name] = []
            products_by_category[category_name].append(item)
        
        # Sortuj slownik kategorii
        products_by_category = {k: products_by_category[k] for k in sorted(products_by_category.keys())}
        
        # Przygotuj odpowiedz HTTP jako PDF
        response = HttpResponse(content_type='application/pdf')
        filename = f"lista_zakupow_{slugify(shopping_list.name)}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Sprawdź dostępność bibliotek
        try:
            # Utworz PDF uzywajac reportlab
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            
            # Zarejestruj podstawowa czcionke z obsluga polskich znakow
            # Uzywamy Helvetica jako podstawowej czcionki, ktora jest wbudowana w ReportLab
            helvetica_font = 'Helvetica'
            helvetica_bold_font = 'Helvetica-Bold'
            
            # Utworz dokument PDF
            pdf = SimpleDocTemplate(
                response,
                pagesize=A4,
                title=f"Lista zakupow: {shopping_list.name}",
                author=request.user.username,
                encoding='utf-8'
            )
            
            # Przygotuj style
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='ListTitle',
                parent=styles['Heading1'],
                fontName=helvetica_bold_font,
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=12
            ))
            styles.add(ParagraphStyle(
                name='CategoryHeading',
                parent=styles['Heading2'],
                fontName=helvetica_bold_font,
                fontSize=14,
                spaceBefore=12,
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='Info',
                parent=styles['Normal'],
                fontName=helvetica_font,
                fontSize=9,
                textColor=colors.gray
            ))
            
            # Przygotuj elementy dokumentu
            elements = []
            
            # Naglowek dokumentu
            elements.append(Paragraph(f"Lista zakupow: {shopping_list.name}", styles['ListTitle']))
            
            # Informacje o liscie
            elements.append(Paragraph(f"Data utworzenia: {shopping_list.created_at.strftime('%d.%m.%Y')}", styles['Info']))
            elements.append(Paragraph(f"Uzytkownik: {shopping_list.user.username}", styles['Info']))
            elements.append(Paragraph(f"Data wygenerowania: {timezone.now().strftime('%d.%m.%Y')}", styles['Info']))
            elements.append(Spacer(1, 12))
            
            # Dodaj listy produktow wedlug kategorii
            for category, products in products_by_category.items():
                # Naglowek kategorii
                elements.append(Paragraph(category, styles['CategoryHeading']))
                
                # Tabela z produktami
                data = [['Skladnik', 'Ilosc', 'Jednostka', 'Kupiono']]
                
                for item in products:
                    data.append([
                        item.ingredient.name,
                        f"{item.amount:.2f}".rstrip('0').rstrip('.') if item.amount % 1 == 0 else f"{item.amount:.2f}",
                        item.unit.name,
                        '✓' if item.is_purchased else ''
                    ])
                
                # Szerokosci kolumn
                col_widths = [250, 70, 90, 40]
                
                # Utworz tabele
                table = Table(data, colWidths=col_widths)
                
                # Style tabeli
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), helvetica_bold_font),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 1), (-1, -1), helvetica_font),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                ])
                
                # Dodaj alternatywne kolory wierszy
                for i in range(1, len(data), 2):
                    table_style.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)
                
                # Zaznacz kupione produkty
                for i, item in enumerate(products, 1):
                    if item.is_purchased:
                        table_style.add('BACKGROUND', (0, i), (-1, i), colors.lightgreen)
                
                # Zastosuj style do tabeli
                table.setStyle(table_style)
                
                # Dodaj tabele do elementow
                elements.append(table)
                elements.append(Spacer(1, 10))
            
            # Dodaj stopke
            footer_style = ParagraphStyle(
                name='Footer',
                parent=styles['Normal'],
                fontName=helvetica_font,
                fontSize=8,
                textColor=colors.gray,
                alignment=TA_CENTER
            )
            elements.append(Spacer(1, 20))
            elements.append(Paragraph('Wygenerowano z aplikacji Ksiazka Kucharska', footer_style))
            
            # Wygeneruj PDF
            pdf.build(elements)
            
            return response
        except ImportError:
            # Jeśli ReportLab nie jest dostępny, spróbuj użyć alternatywnych bibliotek
            if WEASYPRINT_AVAILABLE:
                # Kod generowania PDF za pomocą WeasyPrint
                html_string = render_to_string(
                    'shopping/shopping_list_pdf.html',
                    {'shopping_list': shopping_list, 'products_by_category': products_by_category}
                )
                
                html = HTML(string=html_string)
                main_doc = html.render()
                
                # Zapisz PDF do odpowiedzi HTTP
                main_doc.write_pdf(response)
                return response
            else:
                # Jeśli żadna biblioteka nie jest dostępna, wyświetl komunikat
                messages.warning(request, "Generowanie PDF jest niedostępne. Brak wymaganych bibliotek.")
                return redirect('shopping:detail', pk=pk)
            
    except Exception as e:
        logger.exception(f"Blad podczas generowania PDF: {str(e)}")
        messages.error(request, f'Wystąpił błąd podczas generowania PDF: {str(e)}')
        return redirect('shopping:detail', pk=pk)

@login_required
def normalize_shopping_list(request, pk):
    """
    Konsoliduje produkty na liście zakupów, łącząc te same składniki
    i konwertując je do jednostek podstawowych.
    """
    shopping_list = get_object_or_404(ShoppingList, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            # Wykonaj konsolidację
            consolidated_count = shopping_list.normalize_units()
            
            if consolidated_count > 0:
                messages.success(request, f'Skonsolidowano {consolidated_count} produktów na liście zakupów.')
            else:
                messages.info(request, 'Nie było potrzeby konsolidacji - produkty już mają optymalne jednostki.')
                
        except Exception as e:
            messages.error(request, f'Wystąpił błąd podczas konsolidacji: {str(e)}')
            
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    return render(request, 'shopping/normalize_confirm.html', {
        'shopping_list': shopping_list
    })