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

@login_required
def recipe_list(request):
    recipes = Recipe.objects.filter(user=request.user)
    return render(request, 'recipes/recipe_list.html', {'recipes': recipes})

@login_required
def add_recipe(request):
    IngredientFormSet = inlineformset_factory(Recipe, RecipeIngredient, form=RecipeIngredientForm, extra=0, can_delete=True)
    StepFormSet = inlineformset_factory(Recipe, PreparationStep, form=PreparationStepForm, extra=0, can_delete=True)

    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        ingredient_formset = IngredientFormSet(request.POST)
        step_formset = StepFormSet(request.POST)

        if form.is_valid() and ingredient_formset.is_valid() and step_formset.is_valid():
            recipe = form.save(commit=False)
            recipe.user = request.user
            recipe.save()
            messages.success(request, 'Przepis został zapisany!')

            ingredients = ingredient_formset.save(commit=False)
            for ingredient in ingredients:
                ingredient.recipe = recipe
                ingredient.save()

            steps = step_formset.save(commit=False)
            for index, step in enumerate(steps):
                step.recipe = recipe
                step.order = index + 1
                step.save()

            return redirect('recipe_list')
    else:
        form = RecipeForm()
        ingredient_formset = IngredientFormSet()
        step_formset = StepFormSet()

    return render(request, 'recipes/add_recipe.html', {
        'form': form,
        'ingredient_formset': ingredient_formset,
        'step_formset': step_formset,
    })

@login_required
def check_ingredients(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    fridge_items = FridgeItem.objects.filter(user=request.user)

    missing_ingredients = []

    for ingredient in recipe.ingredients.all():
        matching_item = fridge_items.filter(name__iexact=ingredient.name).first()

        if not matching_item:
            missing_ingredients.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name}')
            add_to_shopping_list(request.user, ingredient, recipe)
        elif matching_item.quantity < ingredient.quantity:
            missing_ingredients.append(f'{ingredient.quantity} {ingredient.unit} {ingredient.name} (masz za mało: {matching_item.quantity} {matching_item.unit})')
            add_to_shopping_list(request.user, ingredient, recipe)

    return render(request, 'recipes/check_ingredients.html', {
        'recipe': recipe,
        'missing_ingredients': missing_ingredients,
    })

def add_to_shopping_list(user, ingredient, recipe):
    item, created = ShoppingItem.objects.get_or_create(
        user=user,
        name=ingredient.name,
        unit=ingredient.unit,
        recipe_name=recipe.name,
        defaults={'quantity': 0}
    )
    item.quantity += ingredient.quantity
    item.save()


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
def edit_recipe(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)

    IngredientFormSet = inlineformset_factory(Recipe, RecipeIngredient, form=RecipeIngredientForm, extra=0, can_delete=True)
    StepFormSet = inlineformset_factory(Recipe, PreparationStep, form=PreparationStepForm, extra=0, can_delete=True)

    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        ingredient_formset = IngredientFormSet(request.POST, instance=recipe)
        step_formset = StepFormSet(request.POST, instance=recipe)

        if form.is_valid() and ingredient_formset.is_valid() and step_formset.is_valid():
            form.save()

            ingredients = ingredient_formset.save(commit=False)
            for ingredient in ingredients:
                ingredient.recipe = recipe
                ingredient.save()

            for obj in ingredient_formset.deleted_objects:
                obj.delete()

            steps = step_formset.save(commit=False)
            for index, step in enumerate(steps):
                step.recipe = recipe
                step.order = index + 1
                step.save()

            for obj in step_formset.deleted_objects:
                obj.delete()

            return redirect('recipe_list')
    else:
        form = RecipeForm(instance=recipe)
        ingredient_formset = IngredientFormSet(instance=recipe)
        step_formset = StepFormSet(instance=recipe)

    return render(request, 'recipes/edit_recipe.html', {
        'form': form,
        'ingredient_formset': ingredient_formset,
        'step_formset': step_formset,
        'recipe': recipe,
    })


@login_required
def delete_recipe(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    if request.method == 'POST':
        recipe.delete()
        messages.success(request, f'Przepis "{recipe.name}" został usunięty.')
        return redirect('recipe_list')

    return render(request, 'recipes/confirm_delete_recipe.html', {'recipe': recipe})


@login_required
def recipe_detail(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})


@login_required
def search_recipes(request):
    query = request.GET.get('q')
    only_possible = request.GET.get('only_possible', 'off') == 'on'

    recipes = Recipe.objects.filter(user=request.user)

    if query:
        recipes = recipes.filter(
            Q(ingredients__name__icontains=query)
        ).distinct()

    if only_possible:
        recipes = [recipe for recipe in recipes if can_be_made_from_fridge(recipe, request.user)]

    return render(request, 'recipes/search_results.html', {'recipes': recipes, 'query': query, 'only_possible': only_possible})

def can_be_made_from_fridge(recipe, user):
    fridge_items = {item.name.lower(): item for item in FridgeItem.objects.filter(user=user)}

    for ingredient in recipe.ingredients.all():
        fridge_item = fridge_items.get(ingredient.name.lower())
        if not fridge_item:
            return False

        if not units_match(ingredient.unit, fridge_item.unit):
            return False

        if fridge_item.quantity < ingredient.quantity:
            return False

    return True

def units_match(recipe_unit, fridge_unit):
    return recipe_unit == fridge_unit


@login_required
def prepare_meal(request, recipe_id):
    recipe = Recipe.objects.get(id=recipe_id, user=request.user)
    fridge_items = {item.name.lower(): item for item in FridgeItem.objects.filter(user=request.user)}

    missing_ingredients = []
    for ingredient in recipe.ingredients.all():
        fridge_item = fridge_items.get(ingredient.name.lower())
        if not fridge_item:
            missing_ingredients.append(f'{ingredient.name} - brakuje całkowicie')
        elif fridge_item.quantity < ingredient.quantity:
            missing_ingredients.append(f'{ingredient.name} - potrzebujesz {ingredient.quantity}, a masz tylko {fridge_item.quantity}')

    if missing_ingredients:
        messages.error(request, "Nie możesz przygotować posiłku, brakuje składników:")
        for missing in missing_ingredients:
            messages.error(request, missing)
        return redirect('recipe_detail', recipe_id=recipe_id)

    # Aktualizacja lodówki - zmniejszenie ilości
    for ingredient in recipe.ingredients.all():
        fridge_item = fridge_items.get(ingredient.name.lower())
        fridge_item.quantity -= ingredient.quantity
        if fridge_item.quantity <= 0:
            fridge_item.delete()
        else:
            fridge_item.save()

    messages.success(request, f'Posiłek "{recipe.name}" został przygotowany, składniki zostały zużyte.')
    return redirect('recipe_detail', recipe_id=recipe_id)

class RecipeListView(ListView):
    model = Recipe
    template_name = 'recipes/recipe_list.html'
    context_object_name = 'recipes'
    paginate_by = 12
    
    def get_queryset(self):
        # Pobierz wszystkie przepisy, bez filtrowania po autorze na początek
        queryset = Recipe.objects.all()
        
        # Filtrowanie po kategorii
        category = self.request.GET.get('category')
        if category and category != 'None':
            queryset = queryset.filter(categories__id=category)
        
        # Filtrowanie po wyszukiwanej frazie - musi być przed konwersją do listy
        query = self.request.GET.get('q')
        if query and query != 'None':
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(ingredients__ingredient__name__icontains=query)
            ).distinct()
        
        # Filtrowanie po konkretnym składniku
        ingredient_id = self.request.GET.get('ingredient')
        if ingredient_id and ingredient_id != 'None':
            queryset = queryset.filter(ingredients__ingredient_id=ingredient_id).distinct()
            
        # Filtrowanie po dostępnych składnikach - musi być przed konwersją do listy
        if self.request.GET.get('available_only') and self.request.GET.get('available_only') != 'None' and self.request.user.is_authenticated:
            available_recipes = []
            for recipe in queryset:
                if recipe.can_be_prepared_with_available_ingredients(self.request.user):
                    available_recipes.append(recipe.id)
            queryset = queryset.filter(id__in=available_recipes)
        
        # Filtrowanie po typie diety - używamy QuerySet.filter() zamiast list comprehension
        diet = self.request.GET.get('diet')
        if diet and diet != 'None':
            # Musimy przekonwertować QuerySet do listy, aby móc filtrować po właściwościach
            # Ale robimy to tak, żeby zachować ID przepisów
            recipe_ids = []
            
            if diet == 'vegetarian':
                for recipe in queryset:
                    if recipe.is_vegetarian:
                        recipe_ids.append(recipe.id)
            elif diet == 'vegan':
                for recipe in queryset:
                    if recipe.is_vegan:
                        recipe_ids.append(recipe.id)
            elif diet == 'meat':
                for recipe in queryset:
                    if recipe.is_meat:
                        recipe_ids.append(recipe.id)
            
            # Teraz filtrujemy oryginalny QuerySet według ID
            queryset = queryset.filter(id__in=recipe_ids)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = RecipeCategory.objects.all()
        context['popular_ingredients'] = Ingredient.objects.annotate(
            recipe_count=Count('recipeingredient')
        ).order_by('-recipe_count')[:20]  # Pobieramy 20 najczęściej używanych składników
        
        # Pobierz parametry z URL i upewnij się, że 'None' nie jest przekazywane do szablonu
        category = self.request.GET.get('category')
        context['selected_category'] = category if category and category != 'None' else None
        
        diet = self.request.GET.get('diet')
        context['selected_diet'] = diet if diet and diet != 'None' else None
        
        query = self.request.GET.get('q')
        context['query'] = query if query and query != 'None' else None
        
        ingredient_id = self.request.GET.get('ingredient')
        context['selected_ingredient'] = ingredient_id if ingredient_id and ingredient_id != 'None' else None
        
        if ingredient_id and ingredient_id != 'None':
            context['ingredient_name'] = Ingredient.objects.filter(id=ingredient_id).first().name
        
        available_only = self.request.GET.get('available_only')
        context['available_only'] = available_only if available_only and available_only != 'None' else None
        
        # Sprawdź, czy użytkownik jest zalogowany
        if self.request.user.is_authenticated:
            # Pobierz ID ulubionych przepisów użytkownika
            favorite_ids = FavoriteRecipe.objects.filter(
                user=self.request.user
            ).values_list('recipe_id', flat=True)
            
            # Przygotuj dane o dostępności przepisów i ulubionych
            for recipe in context['recipes']:
                recipe.is_available = recipe.can_be_prepared_with_available_ingredients(self.request.user)
                recipe.is_favorite = recipe.id in favorite_ids
        
        return context

class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/recipe_detail.html'
    context_object_name = 'recipe'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dodaj informacje o skali przepisu
        servings = self.request.GET.get('servings')
        if servings:
            try:
                servings = int(servings)
                if servings > 0:
                    # Przekazanie oryginalnych i przeskalowanych składników
                    context['servings'] = servings
                    context['original_servings'] = self.object.servings
                    context['scaled_ingredients'] = self.object.scale_to_servings(servings)
            except ValueError:
                pass
        
        # Sprawdź czy użytkownik jest zalogowany
        if self.request.user.is_authenticated:
            # Dodaj informację, czy przepis jest w ulubionych
            context['is_favorite'] = FavoriteRecipe.objects.filter(
                user=self.request.user, 
                recipe=self.object
            ).exists()
            
            # Dodaj informację, czy przepis jest polubiony przez użytkownika
            context['is_liked'] = self.object.is_liked_by(self.request.user)
        
        # Dodaj drobne informacje o przepisie
        context['can_be_prepared'] = False
        if self.request.user.is_authenticated:
            context['can_be_prepared'] = self.object.can_be_prepared_with_available_ingredients(self.request.user)
            context['missing_ingredients'] = self.object.get_missing_ingredients(self.request.user)
            
        # Dodaj formularz do komentowania
        context['comment_form'] = CommentForm()
        
        # Pobierz komentarze do przepisu (tylko główne, bez odpowiedzi)
        context['comments'] = self.object.comments.filter(parent=None)
        
        return context
        
    def post(self, request, *args, **kwargs):
        """Obsługa dodawania komentarzy przez POST"""
        self.object = self.get_object()
        
        if not request.user.is_authenticated:
            messages.error(request, "Musisz być zalogowany, aby dodawać komentarze.")
            return HttpResponseRedirect(self.object.get_absolute_url())
        
        comment_form = CommentForm(request.POST)
        
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.user = request.user
            new_comment.recipe = self.object
            
            # Sprawdź, czy to odpowiedź na komentarz
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent_comment = get_object_or_404(Comment, id=parent_id)
                new_comment.parent = parent_comment
            
            new_comment.save()
            messages.success(request, "Komentarz został dodany.")
            return HttpResponseRedirect(self.object.get_absolute_url())
        
        # Jeśli formularz nie jest poprawny, renderuj stronę z błędami
        context = self.get_context_data(object=self.object)
        context['comment_form'] = comment_form
        return self.render_to_response(context)

class RecipeCreateView(LoginRequiredMixin, CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['ingredient_formset'] = RecipeIngredientFormSet(self.request.POST, prefix='ingredients')
            print(f"POST data: {self.request.POST}")
            print(f"Formset is valid: {context['ingredient_formset'].is_valid()}")
            if not context['ingredient_formset'].is_valid():
                print(f"Formset errors: {context['ingredient_formset'].errors}")
                print(f"Formset non-form errors: {context['ingredient_formset'].non_form_errors()}")
                print(f"Management form data: {self.request.POST.get('ingredients-TOTAL_FORMS')}, {self.request.POST.get('ingredients-INITIAL_FORMS')}, {self.request.POST.get('ingredients-MIN_NUM_FORMS')}")
                
                # Sprawdź, czy dane wchodzą prawidłowo
                for i in range(int(self.request.POST.get('ingredients-TOTAL_FORMS', 0))):
                    ingredient_id = self.request.POST.get(f'ingredients-{i}-ingredient')
                    amount = self.request.POST.get(f'ingredients-{i}-amount')
                    unit_id = self.request.POST.get(f'ingredients-{i}-unit')
                    print(f"Ingredient {i}: ingredient_id={ingredient_id}, amount={amount}, unit_id={unit_id}")
        else:
            context['ingredient_formset'] = RecipeIngredientFormSet(prefix='ingredients')
            
        context['ingredient_categories'] = IngredientCategory.objects.all()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        ingredient_formset = context['ingredient_formset']
        
        print(f"Form valid, checking ingredient formset. Is valid: {ingredient_formset.is_valid()}")
        
        if ingredient_formset.is_valid():
            self.object = form.save(commit=False)
            self.object.author = self.request.user
            self.object.save()
            form.save_m2m()  # Zapisz relacje many-to-many
            
            # Zapisz składniki
            ingredient_forms = ingredient_formset.save(commit=False)
            print(f"Number of ingredient forms: {len(ingredient_forms)}")
            
            # Usuń składniki oznaczone do usunięcia
            for obj in ingredient_formset.deleted_objects:
                print(f"Deleting ingredient: {obj}")
                obj.delete()
            
            # Zapisz nowe i zaktualizowane składniki
            for ingredient_form in ingredient_forms:
                ingredient_form.recipe = self.object
                ingredient_form.save()
                print(f"Saved ingredient: {ingredient_form.ingredient.name}, {ingredient_form.amount} {ingredient_form.unit.name}")
            
            # Wyświetl komunikat z liczbą dodanych składników
            messages.success(
                self.request, 
                f'Przepis "{self.object.title}" został dodany wraz z {len(ingredient_forms)} składnikami!'
            )
            
            return redirect(self.get_success_url())
        else:
            # Jeśli formularz składników jest nieprawidłowy, pokaż błędy
            for error in ingredient_formset.errors:
                messages.error(self.request, f"Błąd składnika: {error}")
            for error in ingredient_formset.non_form_errors():
                messages.error(self.request, f"Ogólny błąd: {error}")
                
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        # Przekieruj na listę przepisów zamiast na szczegóły przepisu
        return reverse_lazy('recipes:list')

class RecipeUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'
    
    def test_func(self):
        recipe = self.get_object()
        return recipe.author == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['ingredient_formset'] = RecipeIngredientFormSet(
                self.request.POST, instance=self.object, prefix='ingredients'
            )
        else:
            context['ingredient_formset'] = RecipeIngredientFormSet(instance=self.object, prefix='ingredients')
        context['ingredient_categories'] = IngredientCategory.objects.all()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        ingredient_formset = context['ingredient_formset']
        
        print(f"Form valid, checking ingredient formset. Is valid: {ingredient_formset.is_valid()}")
        
        if ingredient_formset.is_valid():
            self.object = form.save()
            ingredient_formset.instance = self.object
            ingredient_formset.save()
            
            messages.success(self.request, 'Przepis został zaktualizowany!')
            return redirect(self.get_success_url())
        else:
            # Jeśli formularz składników jest nieprawidłowy, pokaż błędy
            for error in ingredient_formset.errors:
                messages.error(self.request, f"Błąd składnika: {error}")
            for error in ingredient_formset.non_form_errors():
                messages.error(self.request, f"Ogólny błąd: {error}")
                
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse('recipes:detail', kwargs={'pk': self.object.pk})

class RecipeDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Recipe
    template_name = 'recipes/recipe_confirm_delete.html'
    success_url = reverse_lazy('recipes:list')
    
    def test_func(self):
        recipe = self.get_object()
        return self.request.user == recipe.author
    
    def delete(self, request, *args, **kwargs):
        recipe = self.get_object()
        messages.success(request, f'Przepis "{recipe.title}" został usunięty.')
        return super().delete(request, *args, **kwargs)

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
    shopping_lists = ShoppingList.objects.filter(user=request.user, is_completed=False)
    
    context = {
        'recipe': recipe,
        'shopping_lists': shopping_lists
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

@login_required
def prepare_recipe(request, pk):
    """Usuwa składniki przepisu z lodówki po jego przygotowaniu"""
    recipe = get_object_or_404(Recipe, pk=pk)
    
    # Pobierz liczbę porcji z URL (parametr GET) lub ustaw domyślną
    servings_param = request.GET.get('servings')
    servings = None
    
    if servings_param:
        try:
            servings = int(servings_param)
        except (ValueError, TypeError):
            servings = recipe.servings
    else:
        servings = recipe.servings
    
    # Przygotuj skalowane składniki, jeśli podano liczbę porcji
    scaled_ingredients = None
    missing_ingredients = None
    
    if servings and servings != recipe.servings:
        scaled_ingredients = recipe.scale_to_servings(servings)
        
    # Sprawdź dostępność składników w lodówce
    scale_factor = servings / recipe.servings
    missing_ingredients = []
    
    for ingredient_entry in recipe.ingredients.all():
        amount_needed = ingredient_entry.amount * scale_factor
        unit = ingredient_entry.unit
        ingredient = ingredient_entry.ingredient
        
        # Sprawdź dostępność
        available = FridgeItem.check_ingredient_availability(
            request.user, ingredient, amount_needed, unit
        )
        
        if not available:
            # Sprawdź dostępną ilość w lodówce
            items = FridgeItem.objects.filter(
                user=request.user,
                ingredient=ingredient
            )
            
            total_available = 0
            for item in items:
                if item.unit != unit:
                    try:
                        converted_amount = convert_units(item.amount, item.unit, unit)
                        total_available += converted_amount
                    except ValueError:
                        pass
                else:
                    total_available += item.amount
            
            missing_ingredients.append({
                'ingredient': ingredient,
                'required': amount_needed,
                'available': total_available,
                'missing': amount_needed - total_available,
                'unit': unit
            })
    
    # Jeśli nie brakuje składników, ustaw na None
    if not missing_ingredients:
        missing_ingredients = None
    
    if request.method == 'POST':
        post_servings = request.POST.get('servings')
        
        try:
            post_servings = int(post_servings)
        except (ValueError, TypeError):
            post_servings = recipe.servings
            
        # Usuń składniki z lodówki
        result = FridgeItem.use_recipe_ingredients(request.user, recipe, post_servings)
        
        if result['success']:
            messages.success(request, f'Przygotowałeś przepis "{recipe.title}" ({post_servings} porcji). Składniki zostały usunięte z lodówki.')
            return redirect('recipes:detail', pk=recipe.pk)
        else:
            missing_text = ", ".join([f"{item['ingredient'].name}" for item in result['missing']])
            messages.warning(request, f'Nie możesz przygotować tego przepisu - brakuje składników: {missing_text}')
            
            # Przekieruj do formularza dodawania brakujących składników do listy zakupów
            return redirect('recipes:add_missing_to_shopping_list', pk=recipe.pk)
    
    context = {
        'recipe': recipe,
        'servings': servings,
        'scaled_ingredients': scaled_ingredients,
        'missing_ingredients': missing_ingredients
    }
    
    return render(request, 'recipes/prepare_recipe.html', context)

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
                # Pobierz wszystkie składniki z danej kategorii
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

def ajax_load_units(request):
    """Pobieranie jednostek miary dla składnika za pomocą AJAX"""
    units = MeasurementUnit.objects.all()
    units_data = [{'id': u.id, 'name': u.name} for u in units]
    return JsonResponse({'units': units_data})

class IngredientListView(LoginRequiredMixin, ListView):
    model = Ingredient
    template_name = 'recipes/ingredient_list.html'
    context_object_name = 'ingredients'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = IngredientCategory.objects.all()
        return context

class IngredientCreateView(LoginRequiredMixin, CreateView):
    model = Ingredient
    form_class = IngredientForm
    template_name = 'recipes/ingredient_form.html'
    success_url = reverse_lazy('recipes:ingredient_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Składnik został dodany!')
        return super().form_valid(form)

class IngredientUpdateView(LoginRequiredMixin, UpdateView):
    model = Ingredient
    form_class = IngredientForm
    template_name = 'recipes/ingredient_form.html'
    success_url = reverse_lazy('recipes:ingredient_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Składnik został zaktualizowany!')
        return super().form_valid(form)

class IngredientDeleteView(LoginRequiredMixin, DeleteView):
    model = Ingredient
    template_name = 'recipes/ingredient_confirm_delete.html'
    success_url = reverse_lazy('recipes:ingredient_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Składnik został usunięty!')
        return super().delete(request, *args, **kwargs)

@login_required
def ajax_add_ingredient(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description', '')
        
        if not name or not category_id:
            return JsonResponse({
                'success': False,
                'errors': {
                    'name': ['To pole jest wymagane.'] if not name else [],
                    'category': ['To pole jest wymagane.'] if not category_id else []
                }
            })
        
        try:
            category = IngredientCategory.objects.get(pk=category_id)
            ingredient = Ingredient.objects.create(
                name=name,
                category=category,
                description=description
            )
            
            return JsonResponse({
                'success': True,
                'id': ingredient.id,
                'name': ingredient.name,
                'message': 'Składnik został dodany!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': {'server': [str(e)]}
            })
    
    return JsonResponse({'success': False, 'message': 'Nieprawidłowe żądanie'})

@login_required
@require_POST
def toggle_favorite(request, pk):
    """Dodaje lub usuwa przepis z ulubionych"""
    try:
        recipe = get_object_or_404(Recipe, pk=pk)
        favorite, created = FavoriteRecipe.objects.get_or_create(user=request.user, recipe=recipe)
        
        if not created:
            # Jeśli przepis był już w ulubionych, usuń go
            favorite.delete()
            is_favorite = False
        else:
            is_favorite = True
        
        return JsonResponse({
            'status': 'success',
            'is_favorite': is_favorite,
            'message': 'Przepis dodany do ulubionych' if is_favorite else 'Przepis usunięty z ulubionych'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
@require_POST
def toggle_like(request, pk):
    """Przełącza polubienie przepisu (dodaje/usuwa)"""
    recipe = get_object_or_404(Recipe, pk=pk)
    
    # Przełącz polubienie
    liked = recipe.toggle_like(request.user)
    
    # Jeśli to żądanie AJAX, zwróć odpowiedź JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': liked,
            'likes_count': recipe.likes_count
        })
    
    # W przeciwnym razie, przekieruj z powrotem do strony przepisu
    return HttpResponseRedirect(reverse('recipes:detail', args=[pk]))

@login_required
@require_POST
def delete_comment(request, pk):
    """Usuwa komentarz"""
    comment = get_object_or_404(Comment, pk=pk)
    
    # Sprawdź, czy użytkownik ma uprawnienia do usunięcia komentarza
    if comment.user != request.user and not request.user.is_staff:
        messages.error(request, "Nie masz uprawnień do usunięcia tego komentarza.")
        return HttpResponseRedirect(comment.recipe.get_absolute_url())
    
    recipe_url = comment.recipe.get_absolute_url()
    comment.delete()
    
    messages.success(request, "Komentarz został usunięty.")
    return HttpResponseRedirect(recipe_url)

def home_view(request):
    """Widok strony głównej z najpopularniejszymi przepisami"""
    # Pobierz przepisy z największą liczbą polubień (limit 8)
    popular_recipes = Recipe.objects.annotate(
        likes_total=Count('likes')
    ).order_by('-likes_total', '-created_at')[:8]
    
    # Przekaż przepisy do szablonu
    context = {
        'popular_recipes': popular_recipes
    }
    
    return render(request, 'home.html', context)

@login_required
def export_meal_plan_to_pdf(request):
    """Eksportuje aktualny widok planera posiłków do PDF"""
    # Pobierz datę początkową (poniedziałek bieżącego tygodnia)
    today = date.today()
    start_date_param = request.GET.get('start_date')
    
    if start_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=today.weekday())
    else:
        # Jeśli nie podano daty, użyj poniedziałku bieżącego tygodnia
        start_date = today - timedelta(days=today.weekday())
    
    # Generuj daty dla całego tygodnia (pon-niedz)
    dates = [start_date + timedelta(days=i) for i in range(7)]
    
    # Pobierz wszystkie posiłki z tego okresu dla zalogowanego użytkownika
    meal_plans = MealPlan.objects.filter(
        user=request.user,
        date__range=(dates[0], dates[6])
    ).order_by('date', 'meal_type')
    
    # Przygotuj dane dla PDF
    # Utwórz bufor pamięci do zapisania PDF
    buffer = io.BytesIO()
    
    # Utwórz obiekt canvas z bufforem (użyj widoku landscape)
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    
    # Ustaw czcionkę
    p.setFont("Helvetica-Bold", 16)
    
    # Tytuł dokumentu
    p.drawString(2*cm, 19*cm, f"Plan posiłków od {dates[0].strftime('%d.%m.%Y')} do {dates[6].strftime('%d.%m.%Y')}")
    
    # Wypisz informacje
    p.setFont("Helvetica", 12)
    p.drawString(2*cm, 18*cm, f"Użytkownik: {request.user.username}")
    
    # Przygotuj dane do tabeli
    meal_type_names = {meal_type: name for meal_type, name in MealPlan.MEAL_TYPES}
    
    # Nagłówki tabeli - dni tygodnia
    headers = ["Posiłek"]
    for day_date in dates:
        headers.append(f"{day_date.strftime('%a %d.%m')}")
    
    # Dane tabeli - rodzaje posiłków i ich zawartość
    data = [headers]
    
    for meal_type, meal_name in MealPlan.MEAL_TYPES:
        row = [meal_name]
        
        for day_date in dates:
            # Znajdź posiłek dla tego dnia i typu
            meal = meal_plans.filter(date=day_date, meal_type=meal_type).first()
            
            if meal:
                if meal.recipe:
                    cell_text = f"{meal.recipe.title} ({meal.servings} porcji)"
                else:
                    cell_text = f"{meal.custom_name or 'Własny posiłek'}"
                
                if meal.completed:
                    cell_text = f"✓ {cell_text}"
            else:
                cell_text = "-"
                
            row.append(cell_text)
            
        data.append(row)
    
    # Ustaw szerokości kolumn (pierwsza kolumna szersza, reszta równa)
    col_widths = [5*cm] + [3.5*cm] * 7
    
    # Utwórz tabelę
    table = Table(data, colWidths=col_widths)
    
    # Stylizacja tabeli
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Nagłówki kolumn
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),  # Nagłówki wierszy
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Pogrubione nagłówki kolumn
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Pogrubione nagłówki wierszy
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (1, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Rysuj tabelę
    table.wrapOn(p, 2*cm, 2*cm)
    table.drawOn(p, 2*cm, 5*cm)
    
    # Dodaj informacje na końcu strony
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(2*cm, 2*cm, "Wygenerowano z aplikacji Książka Kucharska")
    
    # Zakończ stronę
    p.showPage()
    p.save()
    
    # Zapisz PDF do bufora i zwróć jako odpowiedź
    buffer.seek(0)
    
    # Przygotuj odpowiedź
    filename = f"plan_posilkow_{dates[0].strftime('%Y%m%d')}.pdf"
    response = FileResponse(buffer, as_attachment=True, filename=filename)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def meal_planner(request):
    """Widok tygodniowego planera posiłków"""
    # Pobierz datę początkową (poniedziałek bieżącego tygodnia)
    today = date.today()
    start_date_param = request.GET.get('start_date')
    
    if start_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=today.weekday())
    else:
        # Jeśli nie podano daty, użyj poniedziałku bieżącego tygodnia
        start_date = today - timedelta(days=today.weekday())
    
    # Generuj daty dla całego tygodnia (pon-niedz)
    dates = [start_date + timedelta(days=i) for i in range(7)]
    
    # Pobierz wszystkie posiłki z tego okresu dla zalogowanego użytkownika
    meal_plans = MealPlan.objects.filter(
        user=request.user,
        date__range=(dates[0], dates[6])
    ).order_by('date', 'meal_type')
    
    # Przygotuj dane dla szablonu
    week_data = {}
    for day_date in dates:
        day_name = day_date.strftime('%A')  # Nazwa dnia tygodnia
        day_meals = {}
        
        # Dla każdego typu posiłku sprawdź, czy istnieje zaplanowany posiłek
        for meal_code, meal_name in MealPlan.MEAL_TYPES:
            day_meals[meal_code] = meal_plans.filter(date=day_date, meal_type=meal_code).first()
        
        week_data[day_date] = {
            'name': day_name,
            'date': day_date,
            'meals': day_meals
        }
    
    # Formularz do wyboru tygodnia
    week_form = MealPlanWeekForm(initial={'start_date': start_date})
    
    # Wylicz daty poprzedniego i następnego tygodnia
    prev_week = start_date - timedelta(days=7)
    next_week = start_date + timedelta(days=7)
    
    context = {
        'week_data': week_data,
        'dates': dates,
        'meal_types': MealPlan.MEAL_TYPES,
        'week_form': week_form,
        'prev_week': prev_week,
        'next_week': next_week,
        'current_week': start_date
    }
    
    return render(request, 'recipes/meal_planner.html', context)

@login_required
def add_meal_plan(request, date_str=None, meal_type=None):
    """Widok dodawania posiłku do planera"""
    initial = {}
    
    # Jeśli przekazano datę i typ posiłku, użyj ich jako wartości początkowe
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            initial['date'] = parsed_date
        except ValueError:
            pass
    
    if meal_type:
        initial['meal_type'] = meal_type
    
    if request.method == 'POST':
        form = MealPlanForm(request.POST, user=request.user)
        
        if form.is_valid():
            meal_plan = form.save(commit=False)
            meal_plan.user = request.user
            meal_plan.save()
            
            messages.success(request, 'Posiłek został dodany do planera!')
            
            # Przekieruj z powrotem do planera
            return redirect('recipes:meal_planner')
    else:
        form = MealPlanForm(initial=initial, user=request.user)
    
    context = {
        'form': form,
        'title': 'Dodaj posiłek do planera'
    }
    
    return render(request, 'recipes/meal_plan_form.html', context)

@login_required
def edit_meal_plan(request, pk):
    """Widok edycji zaplanowanego posiłku"""
    meal_plan = get_object_or_404(MealPlan, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = MealPlanForm(request.POST, instance=meal_plan, user=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Posiłek został zaktualizowany!')
            return redirect('recipes:meal_planner')
    else:
        form = MealPlanForm(instance=meal_plan, user=request.user)
    
    context = {
        'form': form,
        'title': 'Edytuj zaplanowany posiłek',
        'meal_plan': meal_plan
    }
    
    return render(request, 'recipes/meal_plan_form.html', context)

@login_required
def delete_meal_plan(request, pk):
    """Widok usuwania zaplanowanego posiłku"""
    meal_plan = get_object_or_404(MealPlan, pk=pk, user=request.user)
    
    if request.method == 'POST':
        meal_plan.delete()
        messages.success(request, 'Zaplanowany posiłek został usunięty!')
        return redirect('recipes:meal_planner')
    
    context = {
        'meal_plan': meal_plan
    }
    
    return render(request, 'recipes/meal_plan_confirm_delete.html', context)

@login_required
def toggle_meal_completed(request, pk):
    """Przełączanie statusu zrealizowania posiłku (AJAX)"""
    meal_plan = get_object_or_404(MealPlan, pk=pk, user=request.user)
    
    # Przełącz status
    meal_plan.completed = not meal_plan.completed
    meal_plan.save()
    
    # Jeśli to żądanie AJAX, zwróć odpowiedź JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'completed': meal_plan.completed,
            'id': meal_plan.id
        })
    
    # W przeciwnym razie, przekieruj do planera
    return redirect('recipes:meal_planner')

@login_required
def copy_day_meals(request, from_date, to_date):
    """Kopiowanie posiłków z jednego dnia na inny"""
    if request.method == 'POST':
        try:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Nieprawidłowy format daty!')
            return redirect('recipes:meal_planner')
        
        # Pobierz wszystkie posiłki z dnia źródłowego
        source_meals = MealPlan.objects.filter(user=request.user, date=from_date)
        
        if not source_meals.exists():
            messages.warning(request, f'Brak posiłków do skopiowania z dnia {from_date}!')
            return redirect('recipes:meal_planner')
        
        # Usuń wszystkie istniejące posiłki z dnia docelowego
        MealPlan.objects.filter(user=request.user, date=to_date).delete()
        
        # Kopiuj posiłki
        copied_count = 0
        for meal in source_meals:
            # Tworzymy kopię posiłku ze zmienioną datą
            meal.pk = None  # Ustawienie None na ID tworzy nowy obiekt
            meal.date = to_date
            meal.save()
            copied_count += 1
        
        messages.success(request, f'Skopiowano {copied_count} posiłków z {from_date} na {to_date}!')
    
    return redirect('recipes:meal_planner')

@login_required
def generate_shopping_list_from_plan(request):
    """Generuje listę zakupów na podstawie zaplanowanych posiłków"""
    if request.method == 'POST':
        # Pobierz daty z formularza
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Nieprawidłowy format daty!')
            return redirect('recipes:meal_planner')
        
        # Pobierz posiłki z wybranego zakresu dat
        meal_plans = MealPlan.objects.filter(
            user=request.user,
            date__range=(start_date, end_date),
            recipe__isnull=False  # Tylko posiłki z przypisanymi przepisami
        )
        
        if not meal_plans.exists():
            messages.warning(request, 'Brak przepisów do wygenerowania listy zakupów w wybranym okresie!')
            return redirect('recipes:meal_planner')
        
        # Sprawdź czy istnieje moduł shopping - jeśli nie, pokaż błąd
        try:
            from shopping.models import ShoppingList
        except ImportError:
            messages.error(request, 'Moduł listy zakupów nie jest dostępny!')
            return redirect('recipes:meal_planner')
        
        # Utwórz nową listę zakupów
        shopping_list = ShoppingList.objects.create(
            user=request.user,
            name=f'Lista zakupów {start_date} - {end_date}'
        )
        
        # Dodaj składniki z przepisów
        total_ingredients = 0
        for meal_plan in meal_plans:
            if meal_plan.recipe:
                # Użyj funkcji get_ingredients_for_shopping, która uwzględnia liczbę porcji
                ingredients = meal_plan.get_ingredients_for_shopping()
                for ingredient_data in ingredients:
                    shopping_list.add_ingredient(
                        ingredient_data['ingredient'],
                        ingredient_data['amount'],
                        ingredient_data['unit']
                    )
                    total_ingredients += 1
        
        # Optymalizuj listę składników (łączenie podobnych)
        shopping_list.optimize()
        
        messages.success(
            request, 
            f'Utworzono listę zakupów z {total_ingredients} składnikami z {meal_plans.count()} posiłków!'
        )
        
        # Przekieruj do szczegółów listy zakupów
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    # Jeśli żądanie GET, przekieruj do planera
    return redirect('recipes:meal_planner')