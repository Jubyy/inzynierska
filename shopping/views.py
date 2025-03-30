from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, FileResponse
from django.db.models import Q
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from django.utils.translation import gettext as _

from .models import ShoppingList, ShoppingItem
from recipes.models import Ingredient, MeasurementUnit, Recipe, IngredientCategory
from .forms import ShoppingListForm, ShoppingItemForm, ShoppingItemFormSet

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
                # Pobierz wszystkie składniki z danej kategorii, nie tylko 10 pierwszych
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

@login_required
def export_list_to_pdf(request, pk):
    """Eksportuje listę zakupów do pliku PDF"""
    shopping_list = get_object_or_404(ShoppingList, pk=pk, user=request.user)
    
    # Utwórz bufor pamięci do zapisania PDF
    buffer = io.BytesIO()
    
    # Utwórz obiekt canvas z bufforem
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Ustaw czcionkę (możesz użyć wbudowanej czcionki)
    p.setFont("Helvetica-Bold", 16)
    
    # Tytuł dokumentu
    p.drawString(2*cm, 28*cm, f"Lista zakupów: {shopping_list.name}")
    
    # Informacje o liście
    p.setFont("Helvetica", 12)
    p.drawString(2*cm, 27*cm, f"Data utworzenia: {shopping_list.created_at.strftime('%d-%m-%Y')}")
    p.drawString(2*cm, 26.5*cm, f"Użytkownik: {shopping_list.user.username}")
    
    # Nagłówki tabeli
    headers = ["Składnik", "Ilość", "Jednostka", "Kupiono"]
    data = [headers]
    
    # Dane tabeli
    for item in shopping_list.items.all():
        row = [
            item.ingredient.name,
            str(round(item.amount, 2)),
            item.unit.symbol,
            "✓" if item.is_purchased else ""
        ]
        data.append(row)
    
    # Utwórz tabelę
    table = Table(data, colWidths=[8*cm, 3*cm, 3*cm, 2*cm])
    
    # Stylizacja tabeli
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Rysuj tabelę
    table.wrapOn(p, 2*cm, 20*cm)
    table.drawOn(p, 2*cm, 24*cm)
    
    # Dodaj informacje na końcu strony
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(2*cm, 2*cm, "Wygenerowano z aplikacji Książka Kucharska")
    
    # Zakończ stronę
    p.showPage()
    p.save()
    
    # Zapisz PDF do bufora i zwróć jako odpowiedź
    buffer.seek(0)
    
    # Przygotuj odpowiedź
    filename = f"lista_zakupow_{shopping_list.id}.pdf"
    response = FileResponse(buffer, as_attachment=True, filename=filename)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response