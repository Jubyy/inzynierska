from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponseRedirect, FileResponse
from .models import Recipe, RecipeIngredient, Ingredient, MeasurementUnit, RecipeCategory, IngredientCategory, UnitConversion, FavoriteRecipe, RecipeLike, Comment
from .utils import convert_units, get_common_units, get_common_conversions
from .forms import RecipeForm, RecipeIngredientFormSet, IngredientForm, CommentForm
from shopping.models import ShoppingItem, ShoppingList
from fridge.models import FridgeItem
from django.views.decorators.http import require_POST
from decimal import Decimal

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

@login_required
def ajax_load_units(request):
    """Widok AJAX do ładowania jednostek dla wybranego składnika"""
    ingredient_id = request.GET.get('ingredient_id')
    
    if not ingredient_id:
        return JsonResponse({'units': [], 'default_unit': None})
    
    try:
        ingredient = get_object_or_404(Ingredient, id=ingredient_id)
        compatible_units = ingredient.compatible_units.all()
        
        if not compatible_units.exists() and ingredient.default_unit:
            compatible_units = [ingredient.default_unit]
        
        units = [
            {
                'id': unit.id, 
                'name': unit.name,
                'symbol': unit.symbol
            } 
            for unit in compatible_units
        ]
        
        default_unit = ingredient.default_unit.id if ingredient.default_unit else None
        
        return JsonResponse({
            'units': units,
            'default_unit': default_unit
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/recipe_detail.html'
    context_object_name = 'recipe'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dodaj informacje o skali przepisu
        servings_param = self.request.GET.get('servings')
        if servings_param:
            try:
                servings = int(servings_param)
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
        else:
            context['ingredient_formset'] = RecipeIngredientFormSet(prefix='ingredients')
            
        context['ingredient_categories'] = IngredientCategory.objects.all()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        ingredient_formset = context['ingredient_formset']
        
        if ingredient_formset.is_valid():
            self.object = form.save(commit=False)
            self.object.author = self.request.user
            self.object.save()
            form.save_m2m()  # Zapisz relacje many-to-many
            
            # Zapisz składniki
            ingredient_forms = ingredient_formset.save(commit=False)
            
            # Usuń składniki oznaczone do usunięcia
            for obj in ingredient_formset.deleted_objects:
                obj.delete()
            
            # Zapisz nowe i zaktualizowane składniki
            for ingredient_form in ingredient_forms:
                ingredient_form.recipe = self.object
                ingredient_form.save()
            
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
    """Przełączanie polubienia przepisu (dodaje/usuwa)"""
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

def ajax_unit_info(request):
    """Widok AJAX do pobierania informacji o jednostce"""
    unit_id = request.GET.get('unit_id')
    amount = request.GET.get('amount', '1')
    
    try:
        unit = get_object_or_404(MeasurementUnit, pk=unit_id)
        amount = float(amount)
        
        # Przygotuj opis jednostki i informację o konwersji
        description = unit.description if unit.description else ''
        
        # Informacja o konwersji
        conversion = ""
        if unit.base_ratio and unit.type in ['weight', 'volume']:
            base_amount = amount * unit.base_ratio
            base_unit = "g" if unit.type == 'weight' else "ml"
            conversion = f"{amount} {unit.name} ≈ {base_amount} {base_unit}"
        
        return JsonResponse({
            'description': description,
            'conversion': conversion
        })
    except Exception as e:
        return JsonResponse({
            'description': '',
            'conversion': '',
            'error': str(e)
        }, status=400) 