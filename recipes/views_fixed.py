from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponseRedirect, FileResponse
from .models import Recipe, RecipeIngredient, Ingredient, MeasurementUnit, RecipeCategory, IngredientCategory, UnitConversion, FavoriteRecipe, RecipeLike, Comment, MealPlan
from .utils import convert_units, get_common_units, get_common_conversions
from .forms import RecipeForm, RecipeIngredientFormSet, IngredientForm, CommentForm, MealPlanForm, MealPlanWeekForm
from shopping.models import ShoppingItem, ShoppingList
from fridge.models import FridgeItem
from django.views.decorators.http import require_POST
from datetime import date, datetime, timedelta
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from decimal import Decimal

# Tutaj skopiuj wszystkie funkcje z oryginalnego pliku views.py

@login_required
def add_to_shopping_list(request, pk):
    """Dodaje składniki przepisu do listy zakupów"""
    recipe = get_object_or_404(Recipe, pk=pk)
    
    if request.method == 'POST':
        # Pobierz lub utwórz listę zakupów
        shopping_list_id = request.POST.get('shopping_list')
        servings = request.POST.get('servings')
        
        try:
            servings = int(servings)
        except (ValueError, TypeError):
            servings = recipe.servings
        
        if shopping_list_id:
            shopping_list = get_object_or_404(ShoppingList, pk=shopping_list_id, user=request.user)
        else:
            # Utwórz nową listę zakupów
            list_name = f"Zakupy dla: {recipe.title}"
            shopping_list = ShoppingList.objects.create(user=request.user, name=list_name)
        
        # Dodaj składniki do listy
        created_items = shopping_list.add_recipe_ingredients(recipe, servings)
        
        messages.success(request, f'Dodano {len(created_items)} składników do listy zakupów "{shopping_list.name}".')
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    # Pobierz istniejące listy zakupów użytkownika
    try:
        shopping_lists = ShoppingList.objects.filter(user=request.user, is_completed=False)
    except Exception:
        shopping_lists = []
        
    missing_ingredients = recipe.get_missing_ingredients(request.user)
    
    context = {
        'recipe': recipe,
        'shopping_lists': shopping_lists,
        'missing_ingredients': missing_ingredients
    }
    
    return render(request, 'recipes/add_to_shopping_list.html', context)

@login_required
def add_missing_to_shopping_list(request, pk):
    """Dodaje brakujące składniki przepisu do listy zakupów"""
    recipe = get_object_or_404(Recipe, pk=pk)
    
    # Obsługa przypadku, gdy tabela shopping_shoppinglist nie istnieje
    try:
        from shopping.models import ShoppingList
    except Exception:
        context = {
            'recipe': recipe,
            'missing_ingredients': recipe.get_missing_ingredients(request.user),
            'table_not_exists': True
        }
        return render(request, 'recipes/add_missing_to_shopping_list.html', context)
    
    if request.method == 'POST':
        # Pobierz lub utwórz listę zakupów
        shopping_list_id = request.POST.get('shopping_list')
        
        if shopping_list_id:
            shopping_list = get_object_or_404(ShoppingList, pk=shopping_list_id, user=request.user)
        else:
            # Utwórz nową listę zakupów
            list_name = f"Brakujące składniki: {recipe.title}"
            shopping_list = ShoppingList.objects.create(user=request.user, name=list_name)
        
        # Dodaj brakujące składniki do listy
        created_items = shopping_list.add_missing_ingredients(recipe)
        
        if created_items:
            messages.success(request, f'Dodano {len(created_items)} brakujących składników do listy zakupów.')
        else:
            messages.info(request, 'Wszystkie składniki do tego przepisu są już dostępne w Twojej lodówce.')
            
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    # Pobierz istniejące listy zakupów użytkownika
    try:
        shopping_lists = ShoppingList.objects.filter(user=request.user, is_completed=False)
    except Exception:
        shopping_lists = []
        
    missing_ingredients = recipe.get_missing_ingredients(request.user)
    
    context = {
        'recipe': recipe,
        'shopping_lists': shopping_lists,
        'missing_ingredients': missing_ingredients
    }
    
    return render(request, 'recipes/add_missing_to_shopping_list.html', context)

def ajax_ingredient_search(request):
    """Widok AJAX do wyszukiwania składników"""
    ingredients = Ingredient.objects.all().order_by('name')
    categories = IngredientCategory.objects.all().order_by('name')
    
    results = []
    for category in categories:
        category_ingredients = ingredients.filter(category=category)
        if category_ingredients:
            results.append({
                'text': category.name,
                'children': [{'id': i.id, 'text': i.name} for i in category_ingredients]
            })
    
    return JsonResponse({'results': results})

def ajax_load_units(request):
    """Pobieranie jednostek miary dla składnika"""
    ingredient_id = request.GET.get('ingredient_id')
    
    try:
        ingredient = Ingredient.objects.get(pk=ingredient_id)
        # Pobierz dozwolone jednostki dla składnika
        allowed_units = ingredient.allowed_units.all()
        
        if not allowed_units:
            # Jeśli nie ma zdefiniowanych jednostek, zwróć wszystkie
            units = MeasurementUnit.objects.all()
        else:
            units = [au.unit for au in allowed_units]
        
        units_data = [{
            'id': unit.id,
            'name': unit.name,
            'is_default': hasattr(unit, 'is_default') and unit.is_default
        } for unit in units]
        
        return JsonResponse({'units': units_data})
    except Ingredient.DoesNotExist:
        return JsonResponse({'units': []}) 