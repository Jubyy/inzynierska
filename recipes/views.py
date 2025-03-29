from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.http import JsonResponse
from .models import Recipe, RecipeIngredient, Ingredient, MeasurementUnit, RecipeCategory, IngredientCategory
from .utils import convert_units, get_common_units, get_common_conversions
from .forms import RecipeForm, RecipeIngredientFormSet, IngredientForm
from shopping.models import ShoppingItem, ShoppingList
from fridge.models import FridgeItem

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
        if category:
            queryset = queryset.filter(categories__id=category)
        
        # Filtrowanie po typie diety
        diet = self.request.GET.get('diet')
        if diet == 'vegetarian':
            queryset = [recipe for recipe in queryset if recipe.is_vegetarian]
        elif diet == 'vegan':
            queryset = [recipe for recipe in queryset if recipe.is_vegan]
        
        # Filtrowanie po wyszukiwanej frazie
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(ingredients__ingredient__name__icontains=query)
            ).distinct()
        
        # Filtrowanie po dostępnych składnikach
        if self.request.GET.get('available_only') and self.request.user.is_authenticated:
            available_recipes = []
            for recipe in queryset:
                if recipe.can_be_prepared_with_available_ingredients(self.request.user):
                    available_recipes.append(recipe.id)
            queryset = queryset.filter(id__in=available_recipes)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = RecipeCategory.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['selected_diet'] = self.request.GET.get('diet')
        context['query'] = self.request.GET.get('q')
        context['available_only'] = self.request.GET.get('available_only')
        
        # Sprawdź, czy użytkownik jest zalogowany
        if self.request.user.is_authenticated:
            # Przygotuj dane o dostępności przepisów
            for recipe in context['recipes']:
                recipe.is_available = recipe.can_be_prepared_with_available_ingredients(self.request.user)
        
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
        
        # Jeśli użytkownik jest zalogowany, dodaj informacje o brakujących składnikach
        if self.request.user.is_authenticated:
            context['missing_ingredients'] = self.object.get_missing_ingredients(self.request.user)
            context['can_be_prepared'] = len(context['missing_ingredients']) == 0
        
        return context

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
    
    if request.method == 'POST':
        servings = request.POST.get('servings')
        
        try:
            servings = int(servings)
        except (ValueError, TypeError):
            servings = recipe.servings
            
        # Usuń składniki z lodówki
        result = FridgeItem.use_recipe_ingredients(request.user, recipe, servings)
        
        if result['success']:
            messages.success(request, f'Przygotowałeś przepis "{recipe.title}". Składniki zostały usunięte z lodówki.')
        else:
            messages.warning(request, 'Nie możesz przygotować tego przepisu - brakuje niektórych składników.')
            
        return redirect('recipes:detail', pk=recipe.pk)
    
    context = {
        'recipe': recipe
    }
    
    return render(request, 'recipes/prepare_recipe.html', context)

def ajax_ingredient_search(request):
    """Wyszukiwanie składników za pomocą AJAX"""
    query = request.GET.get('q', '')
    ingredients = Ingredient.objects.all()
    
    if query:
        ingredients = ingredients.filter(name__icontains=query)
    
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