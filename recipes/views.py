from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Recipe, RecipeIngredient
from .forms import RecipeForm, RecipeIngredientForm
from django.forms import inlineformset_factory
from fridge.models import FridgeItem
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
