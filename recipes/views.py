from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Recipe, RecipeIngredient
from .forms import RecipeForm, RecipeIngredientForm
from django.forms import inlineformset_factory
from fridge.models import FridgeItem
from .utils import convert_units
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.conf import settings
import os
from fridge.models import FridgeItem
from .models import Recipe
from .utils import convert_units

@login_required
def recipe_list(request):
    recipes = Recipe.objects.filter(user=request.user)
    return render(request, 'recipes/recipe_list.html', {'recipes': recipes})

@login_required
def add_recipe(request):
    IngredientFormSet = inlineformset_factory(Recipe, RecipeIngredient, form=RecipeIngredientForm, extra=3)

    if request.method == 'POST':
        form = RecipeForm(request.POST)
        formset = IngredientFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()

            ingredients = formset.save(commit=False)
            for ingredient in ingredients:
                ingredient.recipe = recipe
                ingredient.save()

            return redirect('recipe_list')
    else:
        form = RecipeForm()
        formset = IngredientFormSet()

    return render(request, 'recipes/add_recipe.html', {'form': form, 'formset': formset})


def check_ingredients(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    fridge_items = FridgeItem.objects.filter(user=request.user)

    missing_ingredients = []

    for ingredient in recipe.ingredients.all():
        matching_item = fridge_items.filter(name__iexact=ingredient.name).first()

        if not matching_item:
            # Brak całego składnika
            missing_ingredients.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name}')
        else:
            # Składnik jest, sprawdzamy czy ilość się zgadza
            if ingredient.unit != matching_item.unit:
                converted_quantity = convert_units(matching_item.quantity, matching_item.unit, ingredient.unit)

                if converted_quantity is None:
                    missing_ingredients.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name} (zła jednostka - masz {matching_item.quantity} {matching_item.unit})')
                elif converted_quantity < ingredient.quantity:
                     missing_ingredients.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name} (masz za mało: {matching_item.quantity} {matching_item.unit}, czyli {converted_quantity:.2f} {ingredient.unit})')
            else:
                 if ingredient.quantity > matching_item.quantity:
                      missing_ingredients.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name} (masz za mało: {matching_item.quantity} {matching_item.unit})')

    return render(request, 'recipes/check_ingredients.html', {
        'recipe': recipe,
        'missing_ingredients': missing_ingredients,
    })


@login_required
def scale_recipe(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)

    if request.method == 'POST':
        target_portions = int(request.POST.get('portions', recipe.portions))

        scaled_ingredients = []
        scale_factor = target_portions / recipe.portions

        for ingredient in recipe.ingredients.all():
            scaled_ingredients.append({
                'name': ingredient.name,
                'quantity': round(ingredient.quantity * scale_factor, 2),
                'unit': ingredient.unit,
            })

        return render(request, 'recipes/scale_recipe.html', {
            'recipe': recipe,
            'scaled_ingredients': scaled_ingredients,
            'target_portions': target_portions,
        })

    return render(request, 'recipes/scale_form.html', {'recipe': recipe})


@login_required
def generate_shopping_list(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    fridge_items = FridgeItem.objects.filter(user=request.user)

    shopping_list = []

    for ingredient in recipe.ingredients.all():
        matching_item = fridge_items.filter(name__iexact=ingredient.name).first()

        if not matching_item:
            shopping_list.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name}')
        else:
            # Sprawdź czy mamy odpowiednią ilość, w razie potrzeby konwertuj
            if ingredient.unit != matching_item.unit:
                from .utils import convert_units
                converted_quantity = convert_units(matching_item.quantity, matching_item.unit, ingredient.unit)

                if converted_quantity is None or converted_quantity < ingredient.quantity:
                    needed_quantity = ingredient.quantity - (converted_quantity or 0)
                    shopping_list.append(f'{needed_quantity:.2f} {ingredient.unit} {ingredient.name}')
            elif ingredient.quantity > matching_item.quantity:
                needed_quantity = ingredient.quantity - matching_item.quantity
                shopping_list.append(f'{needed_quantity:.2f} {ingredient.unit} {ingredient.name}')

    return render(request, 'recipes/shopping_list.html', {
        'recipe': recipe,
        'shopping_list': shopping_list,
    })

@login_required
def generate_shopping_list_pdf(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    fridge_items = FridgeItem.objects.filter(user=request.user)

    shopping_list = []

    for ingredient in recipe.ingredients.all():
        matching_item = fridge_items.filter(name__iexact=ingredient.name).first()

        if not matching_item:
            shopping_list.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name}')
        else:
            if ingredient.unit != matching_item.unit:
                converted_quantity = convert_units(matching_item.quantity, matching_item.unit, ingredient.unit)
                if converted_quantity is None or converted_quantity < ingredient.quantity:
                    needed_quantity = ingredient.quantity - (converted_quantity or 0)
                    shopping_list.append(f'{needed_quantity:.2f} {ingredient.unit} {ingredient.name}')
            elif ingredient.quantity > matching_item.quantity:
                needed_quantity = ingredient.quantity - matching_item.quantity
                shopping_list.append(f'{needed_quantity:.2f} {ingredient.unit} {ingredient.name}')

    # Przygotowanie odpowiedzi PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ListaZakupow-{recipe.name}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)

    # Rejestracja czcionki DejaVuSans
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
    p.setFont('DejaVuSans', 12)

    # Tworzenie treści PDF
    width, height = letter
    p.drawString(100, height - 40, f'Lista zakupów dla przepisu: {recipe.name}')

    if shopping_list:
        y = height - 60
        for item in shopping_list:
            p.drawString(100, y, item)
            y -= 20
    else:
        p.drawString(100, height - 60, 'Masz wszystkie składniki! Nie musisz nic kupować.')

    p.showPage()
    p.save()

    return response

@login_required
def edit_recipe(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    IngredientFormSet = inlineformset_factory(Recipe, RecipeIngredient, form=RecipeIngredientForm, extra=0)

    if request.method == 'POST':
        form = RecipeForm(request.POST, instance=recipe)
        formset = IngredientFormSet(request.POST, instance=recipe)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('recipe_list')
    else:
        form = RecipeForm(instance=recipe)
        formset = IngredientFormSet(instance=recipe)

    return render(request, 'recipes/edit_recipe.html', {'form': form, 'formset': formset, 'recipe': recipe})


@login_required
def delete_recipe(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    if request.method == 'POST':
        recipe.delete()
        return redirect('recipe_list')

    return render(request, 'recipes/confirm_delete_recipe.html', {'recipe': recipe})
