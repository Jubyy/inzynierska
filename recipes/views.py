from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponseRedirect, FileResponse
from .models import Recipe, RecipeIngredient, Ingredient, MeasurementUnit, RecipeCategory, IngredientCategory, UnitConversion, FavoriteRecipe, RecipeLike, Comment, ConversionTable, ConversionTableEntry, UserIngredient, RecipeRating, RatingHelpful
from .utils import convert_units, get_common_units, get_common_conversions
from .forms import RecipeForm, RecipeIngredientFormSet, IngredientForm, CommentForm, ConversionTableForm, ConversionEntryForm, RecipeRatingForm
from shopping.models import ShoppingItem, ShoppingList
from fridge.models import FridgeItem
from django.views.decorators.http import require_POST
from decimal import Decimal
from django.utils import timezone
import json
from django.core.paginator import Paginator
import csv
from django.http import HttpResponse

class RecipeListView(ListView):
    model = Recipe
    template_name = 'recipes/recipe_list.html'
    context_object_name = 'recipes'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Recipe.objects.select_related('author').prefetch_related('ingredients').all()
        
        # Filtrowanie po kategorii
        category = self.request.GET.get('category')
        if category and category != 'None':
            queryset = queryset.filter(categories__id=category)
        
        # Filtrowanie po frazie
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
        
        # Filtrowanie po typie diety
        diet = self.request.GET.get('diet')
        if diet and diet != 'None':
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
            
            # Filtruj oryginalny QuerySet według ID
            queryset = queryset.filter(id__in=recipe_ids)
        
        # Filtrowanie po dostępnych składnikach
        if self.request.GET.get('available_only') == 'true' and self.request.user.is_authenticated:
            available_recipe_ids = []
            for recipe in queryset:
                if recipe.can_be_prepared_with_available_ingredients(self.request.user):
                    available_recipe_ids.append(recipe.id)
            queryset = queryset.filter(id__in=available_recipe_ids)
            
        # Filtrowanie po przepisach użytkowników, których śledzimy
        if self.request.GET.get('followed') == 'true' and self.request.user.is_authenticated:
            try:
                # Pobierz ID użytkowników, których śledzi zalogowany użytkownik
                followed_users = self.request.user.following.values_list('followed_user', flat=True)
                queryset = queryset.filter(author__in=followed_users)
            except AttributeError:
                # Jeśli nie ma atrybutu following, wyświetl pusty queryset
                queryset = queryset.none()
        
        # Filtrowanie po czasie przygotowania
        prep_time = self.request.GET.get('prep_time')
        if prep_time and prep_time != 'None':
            if prep_time == 'quick':
                # Przepisy szybkie (do 30 minut)
                queryset = queryset.filter(preparation_time__lte=30)
            elif prep_time == 'medium':
                # Przepisy średnie (30-60 minut)
                queryset = queryset.filter(preparation_time__gt=30, preparation_time__lte=60)
            elif prep_time == 'long':
                # Przepisy długie (powyżej 60 minut)
                queryset = queryset.filter(preparation_time__gt=60)
        
        # Filtrowanie po poziomie trudności
        difficulty = self.request.GET.get('difficulty')
        if difficulty and difficulty in ['easy', 'medium', 'hard'] and difficulty != 'None':
            queryset = queryset.filter(difficulty=difficulty)
            
        # Filtrowanie po średniej ocenie
        min_rating = self.request.GET.get('min_rating')
        if min_rating and min_rating != 'None':
            try:
                min_rating = float(min_rating)
                # Krok 1: Pobierz średnie oceny dla przepisów
                recipes_with_ratings = []
                for recipe in queryset:
                    if recipe.average_rating >= min_rating:
                        recipes_with_ratings.append(recipe.id)
                
                # Krok 2: Filtruj przepisy na podstawie średnich ocen
                queryset = queryset.filter(id__in=recipes_with_ratings)
            except (ValueError, TypeError):
                pass
        
        # Sortowanie
        sort_by = self.request.GET.get('sort_by', 'created_at')  # Domyślnie sortowanie po dacie utworzenia
        sort_order = self.request.GET.get('sort_order', 'desc')  # Domyślnie malejąco
        
        # Mapowanie parametrów sortowania na pola modelu
        sort_fields = {
            'created_at': 'created_at',
            'title': 'title',
            'preparation_time': 'preparation_time',
            'servings': 'servings',
            'difficulty': 'difficulty',
        }
        
        # Dodaj sortowanie po ocenie
        if sort_by == 'rating':
            # Sortowanie po średniej ocenie wymaga specjalnej obsługi
            recipe_list = list(queryset)
            recipe_list.sort(key=lambda r: r.average_rating, reverse=(sort_order == 'desc'))
            # Utwórz listę ID w posortowanej kolejności
            sorted_ids = [recipe.id for recipe in recipe_list]
            
            # Zachowaj kolejność sortowania przy przekazywaniu do szablonu
            clauses = ' '.join(['WHEN id=%s THEN %s' % (pk, i) for i, pk in enumerate(sorted_ids)])
            ordering = 'CASE %s END' % clauses
            
            if sorted_ids:
                queryset = Recipe.objects.filter(id__in=sorted_ids).extra(
                    select={'ordering': ordering}, order_by=('ordering',)
                )
            else:
                queryset = Recipe.objects.none()
        else:
            sort_field = sort_fields.get(sort_by, 'created_at')
            
            if sort_order == 'asc':
                queryset = queryset.order_by(sort_field)
            else:
                queryset = queryset.order_by(f'-{sort_field}')
        
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
        
        # Obsługa parametru filtrowania po dostępnych składnikach
        available_only = self.request.GET.get('available_only')
        context['available_only'] = available_only if available_only and available_only != 'None' else None
        
        # Obsługa parametru filtrowania po śledzonych użytkownikach
        followed = self.request.GET.get('followed')
        context['followed'] = followed if followed and followed != 'None' else None
        
        # Obsługa parametru filtrowania po czasie przygotowania
        prep_time = self.request.GET.get('prep_time')
        context['selected_prep_time'] = prep_time if prep_time and prep_time != 'None' else None
        
        # Obsługa parametru filtrowania po poziomie trudności
        difficulty = self.request.GET.get('difficulty')
        context['selected_difficulty'] = difficulty if difficulty and difficulty != 'None' else None
        
        # Obsługa parametru filtrowania po minimalnej ocenie
        min_rating = self.request.GET.get('min_rating')
        context['min_rating'] = min_rating if min_rating and min_rating != 'None' else None
        
        # Dodaj dostępne oceny do filtrowania
        context['rating_options'] = [
            {'value': '3', 'label': '3+ gwiazdki'},
            {'value': '4', 'label': '4+ gwiazdki'},
            {'value': '4.5', 'label': '4.5+ gwiazdki'}
        ]
        
        # Dodaj opcje sortowania do kontekstu
        sort_by = self.request.GET.get('sort_by', 'created_at')
        sort_order = self.request.GET.get('sort_order', 'desc')
        context['sort_by'] = sort_by
        context['sort_order'] = sort_order
        
        # Dodaj dostępne opcje sortowania do kontekstu
        context['sort_options'] = [
            {'value': 'created_at', 'label': 'Data dodania'},
            {'value': 'title', 'label': 'Nazwa przepisu'},
            {'value': 'preparation_time', 'label': 'Czas przygotowania'},
            {'value': 'servings', 'label': 'Liczba porcji'},
            {'value': 'difficulty', 'label': 'Poziom trudności'},
            {'value': 'rating', 'label': 'Ocena'},
        ]
        
        # Dodaj liczbę śledzonych użytkowników do kontekstu
        if self.request.user.is_authenticated:
            try:
                context['followed_users_count'] = self.request.user.following.count()
            except AttributeError:
                # Jeśli nie ma atrybutu following (prawdopodobnie model UsersFollowing nie istnieje)
                context['followed_users_count'] = 0
        else:
            context['followed_users_count'] = 0
        
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
    from fridge.models import FridgeItem
    
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
    
    # Pobierz liczbę porcji z parametru URL (może pochodzić z ekranu prepare_recipe)
    servings_param = request.GET.get('servings')
    servings = None
    
    if servings_param:
        try:
            servings = int(servings_param)
            if servings <= 0:
                servings = recipe.servings
        except (ValueError, TypeError):
            servings = recipe.servings
    
    if request.method == 'POST':
        # Pobierz lub utwórz listę zakupów
        shopping_list_id = request.POST.get('shopping_list')
        create_new = request.POST.get('create_new', 'true')
        post_servings = request.POST.get('servings', servings_param)
        
        print(f"DEBUG: add_missing_to_shopping_list POST - shopping_list_id: {shopping_list_id}, create_new: {create_new}, post_servings: {post_servings}")
        
        try:
            if post_servings:
                post_servings = int(post_servings)
        except (ValueError, TypeError):
            post_servings = None
        
        if shopping_list_id and create_new != 'true':
            shopping_list = get_object_or_404(ShoppingList, pk=shopping_list_id, user=request.user)
            print(f"DEBUG: Używam istniejącej listy zakupów: ID {shopping_list.id}, nazwa: {shopping_list.name}")
        else:
            # Utwórz nową listę zakupów
            list_name = f"Brakujące składniki: {recipe.title}"
            shopping_list = ShoppingList.objects.create(user=request.user, name=list_name, recipe=recipe)
            print(f"DEBUG: Utworzono nową listę zakupów: ID {shopping_list.id}, nazwa: {shopping_list.name}")
        
        # Sprawdź bezpośrednio, czy są brakujące składniki
        missing_ingredients = recipe.get_missing_ingredients(request.user)
        print(f"DEBUG: Liczba brakujących składników przed wywołaniem add_missing_ingredients: {len(missing_ingredients)}")
        for i, item in enumerate(missing_ingredients):
            ingredient_name = item.ingredient.name if hasattr(item, 'ingredient') else item.get('ingredient', {}).name if hasattr(item.get('ingredient', {}), 'name') else 'Unknown'
            amount = item.amount if hasattr(item, 'amount') else item.get('amount', 'Unknown')
            unit = item.unit.name if hasattr(item, 'unit') and item.unit else (item.get('unit').name if item.get('unit') else 'Unknown')
            print(f"DEBUG: Brakujący składnik #{i+1}: {ingredient_name}, {amount} {unit}")
        
        # Próbujemy najpierw standardową metodą
        created_items = shopping_list.add_missing_ingredients(recipe, servings=post_servings or servings)
        print(f"DEBUG: Liczba utworzonych pozycji: {len(created_items)}")
        
        # Sprawdź, czy lista faktycznie ma pozycje
        list_items = shopping_list.items.all()
        print(f"DEBUG: Lista po dodaniu ma {list_items.count()} pozycji")
        
        # Jeśli lista jest pusta, dodaj elementy bezpośrednio
        if list_items.count() == 0 and missing_ingredients:
            print("DEBUG: Lista jest pusta, dodaję składniki bezpośrednio")
            add_items_directly(shopping_list, recipe, missing_ingredients, post_servings or servings)
            # Sprawdź ponownie po bezpośrednim dodaniu
            list_items = shopping_list.items.all()
            print(f"DEBUG: Lista po bezpośrednim dodaniu ma {list_items.count()} pozycji")
            
        # Wyświetl dodane elementy
        for i, item in enumerate(list_items):
            print(f"DEBUG: Pozycja #{i+1} na liście: {item.ingredient.name}, {item.amount} {item.unit.name}")
        
        # Jeśli dodano elementy, pokaż komunikat sukcesu
        if list_items.count() > 0:
            messages.success(request, f'Dodano {list_items.count()} brakujących składników do listy zakupów.')
        else:
            messages.info(request, 'Wszystkie składniki do tego przepisu są już dostępne w Twojej lodówce.')
            
        return redirect('shopping:detail', pk=shopping_list.pk)
    
    # Pobierz istniejące listy zakupów użytkownika
    try:
        shopping_lists = ShoppingList.objects.filter(user=request.user, is_completed=False)
    except Exception:
        shopping_lists = []
    
    # Przygotuj brakujące składniki w zależności od liczby porcji
    missing_ingredients = []
    
    if servings and servings != recipe.servings:
        # Dla przeskalowanej liczby porcji
        scaled_ingredients = recipe.scale_to_servings(servings)
        
        for scaled_ing in scaled_ingredients:
            ingredient = scaled_ing['ingredient']
            amount = scaled_ing['amount']
            unit = scaled_ing['unit']
            
            if not FridgeItem.check_ingredient_availability(request.user, ingredient, amount, unit):
                # Oblicz brakującą ilość
                total_available = 0.0
                fridge_items = FridgeItem.objects.filter(user=request.user, ingredient=ingredient)
                
                for item in fridge_items:
                    try:
                        # Jeśli jednostki są różne, przelicz
                        if item.unit != unit:
                            converted = convert_units(float(item.amount), item.unit, unit)
                            total_available += converted
                        else:
                            total_available += float(item.amount)
                    except Exception:
                        continue
                
                # Oblicz brakującą ilość
                missing_amount = max(0, float(amount) - total_available)
                
                scaled_missing_ingredients.append({
                    'ingredient': ingredient,
                    'unit': unit,
                    'required': float(amount),
                    'available': total_available,
                    'missing': missing_amount
                })
    else:
        # Dla domyślnej liczby porcji
        # Pobierz brakujące składniki (zwraca listę obiektów RecipeIngredient)
        recipe_missing_ingredients = recipe.get_missing_ingredients(request.user)
        
        # Jeśli nie ma brakujących składników, przekaż pustą listę do szablonu
        if not recipe_missing_ingredients:
            context = {
                'recipe': recipe,
                'shopping_lists': shopping_lists,
                'missing_ingredients': []
            }
            return render(request, 'recipes/add_missing_to_shopping_list.html', context)
        
        # Przekształć obiekty RecipeIngredient na format oczekiwany przez szablon
        for ingredient_entry in recipe_missing_ingredients:
            ingredient = ingredient_entry.ingredient
            unit = ingredient_entry.unit
            required_amount = float(ingredient_entry.amount)
            
            # Pobierz dostępną ilość składnika w lodówce
            available_amount = 0
            fridge_items = FridgeItem.objects.filter(user=request.user, ingredient=ingredient)
            
            for item in fridge_items:
                try:
                    # Jeśli jednostki są różne, przelicz
                    if item.unit != unit:
                        try:
                            converted = convert_units(float(item.amount), item.unit, unit)
                            available_amount += converted
                        except Exception:
                            continue
                    else:
                        available_amount += float(item.amount)
                except Exception:
                    continue
            
            # Oblicz brakującą ilość
            missing_amount = max(0, required_amount - available_amount)
            
            # Dodaj informacje o składniku do listy
            missing_ingredients.append({
                'ingredient': ingredient,
                'unit': unit,
                'required': required_amount,
                'available': available_amount,
                'missing': missing_amount
            })
    
    context = {
        'recipe': recipe,
        'shopping_lists': shopping_lists,
        'missing_ingredients': missing_ingredients,
        'servings': servings or recipe.servings
    }
    
    return render(request, 'recipes/add_missing_to_shopping_list.html', context)

def add_items_directly(shopping_list, recipe, missing_ingredients, servings=None):
    """
    Funkcja pomocnicza do bezpośredniego dodawania brakujących składników do listy zakupów
    """
    from shopping.models import ShoppingItem
    
    # Oblicz współczynnik skalowania
    scale_factor = 1.0
    if servings and servings != recipe.servings:
        scale_factor = float(servings) / float(recipe.servings)
    
    # Iteruj przez brakujące składniki i dodawaj je do listy
    for ingredient_entry in missing_ingredients:
        ingredient = ingredient_entry.ingredient
        unit = ingredient_entry.unit
        amount = float(ingredient_entry.amount) * scale_factor
        
        # Sprawdź, czy składnik już istnieje na liście
        existing_item = shopping_list.items.filter(ingredient=ingredient, unit=unit).first()
        
        if existing_item:
            # Aktualizuj istniejący składnik
            existing_item.amount = max(existing_item.amount, amount)
            existing_item.save()
        else:
            # Utwórz nowy składnik
            ShoppingItem.objects.create(
                shopping_list=shopping_list,
                ingredient=ingredient,
                amount=amount,
                unit=unit,
                recipe=recipe
            )
    
    return shopping_list.items.count()

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
        
        # Pobierz dozwolone jednostki dla składnika
        compatible_units = ingredient.compatible_units.all()
        
        # Jeśli nie ma zdefiniowanych kompatybilnych jednostek, użyj jednostek dozwolonych dla tego składnika
        if not compatible_units.exists():
            compatible_units = ingredient.get_allowed_units()
            
            # Jeśli nadal brak jednostek, użyj domyślnej jednostki lub jednostek dla kategorii
            if not compatible_units.exists():
                if ingredient.default_unit:
                    compatible_units = [ingredient.default_unit]
                else:
                    # W przypadku braku jednostek, użyj domyślnych dla kategorii
                    category_name = ingredient.category.name if ingredient.category else ""
                    compatible_units = MeasurementUnit.get_units_for_ingredient_category(category_name)
        
        # Dla składników typu piece_only upewnij się, że dostępne są tylko jednostki sztukowe
        if ingredient.unit_type == 'piece_only':
            compatible_units = MeasurementUnit.objects.filter(type='piece')
            
            # Jeśli nie ma jednostek sztukowych, dodaj domyślną jednostkę "sztuka"
            if not compatible_units.exists():
                sztuka, _ = MeasurementUnit.objects.get_or_create(
                    symbol='szt',
                    defaults={
                        'name': 'Sztuka',
                        'type': 'piece',
                        'base_ratio': 1.0,
                        'is_common': True
                    }
                )
                compatible_units = [sztuka]
        
        # Przygotuj dane jednostek z dodatkowymi informacjami
        units = []
        for unit in compatible_units:
            unit_data = {
                'id': unit.id, 
                'name': unit.name,
                'symbol': unit.symbol,
                'type': unit.type,
                'base_ratio': float(unit.base_ratio),
                'description': unit.description or '',
                'is_common': unit.is_common,
            }
            
            # Dodaj informacje o przeliczniku dla standardowej ilości
            sample_amount = 100 if unit.type == 'weight' else 1
            if unit.type == 'weight':
                unit_data['conversion'] = f"{sample_amount} {unit.symbol} = {sample_amount * float(unit.base_ratio)} g"
            elif unit.type == 'volume':
                unit_data['conversion'] = f"{sample_amount} {unit.symbol} = {sample_amount * float(unit.base_ratio)} ml"
            elif unit.type == 'piece':
                if ingredient.piece_weight:
                    unit_data['conversion'] = f"1 {unit.symbol} ≈ {float(ingredient.piece_weight)} g"
                else:
                    unit_data['conversion'] = ""
            elif unit.type == 'spoon':
                unit_data['conversion'] = f"{sample_amount} {unit.symbol} = {sample_amount * float(unit.base_ratio)} ml/g"
            
            units.append(unit_data)
        
        # Ustal domyślną jednostkę
        default_unit = ingredient.default_unit.id if ingredient.default_unit else None
        
        # Jeśli nie ma domyślnej jednostki, wybierz najbardziej odpowiednią bazując na unit_type
        if default_unit is None and units:
            unit_type = ingredient.unit_type
            
            # Wybierz odpowiednią jednostkę bazową w zależności od unit_type
            if 'weight' in unit_type:
                gram_unit = next((u for u in units if u['symbol'] == 'g'), None)
                if gram_unit:
                    default_unit = gram_unit['id']
            elif 'volume' in unit_type:
                ml_unit = next((u for u in units if u['symbol'] == 'ml'), None)
                if ml_unit:
                    default_unit = ml_unit['id']
            elif 'piece' in unit_type:
                piece_unit = next((u for u in units if u['type'] == 'piece'), None)
                if piece_unit:
                    default_unit = piece_unit['id']
        
        return JsonResponse({
            'units': units,
            'default_unit': default_unit,
            'category': ingredient.category.name if ingredient.category else "",
            'unit_type': ingredient.unit_type,
            'is_liquid': 'volume' in ingredient.unit_type,
            'is_piece': 'piece' in ingredient.unit_type or ingredient.unit_type == 'piece_only',
            'is_weight': 'weight' in ingredient.unit_type,
            'has_piece_weight': ingredient.piece_weight is not None
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
            
            # Dodaj ocenę użytkownika, jeśli istnieje
            user_rating = self.object.get_user_rating(self.request.user)
            context['user_rating'] = user_rating
            
            # Dodaj formularz oceny
            if user_rating:
                context['rating_form'] = RecipeRatingForm(instance=user_rating)
            else:
                context['rating_form'] = RecipeRatingForm()
        
        # Dodaj drobne informacje o przepisie
        context['can_be_prepared'] = False
        if self.request.user.is_authenticated:
            context['can_be_prepared'] = self.object.can_be_prepared_with_available_ingredients(self.request.user)
            context['missing_ingredients'] = self.object.get_missing_ingredients(self.request.user)
            
        # Dodaj formularz do komentowania
        context['comment_form'] = CommentForm()
        
        # Pobierz komentarze do przepisu (tylko główne, bez odpowiedzi)
        context['comments'] = self.object.comments.filter(parent=None)
        
        # Dodaj statystyki ocen
        context['rating_stats'] = self.object.get_rating_stats()
        
        return context
        
    def post(self, request, *args, **kwargs):
        """Obsługa dodawania komentarzy lub zmiany liczby porcji przez POST"""
        self.object = self.get_object()
        
        # Sprawdź, czy to formularz zmiany porcji (ma parametr servings)
        if 'servings' in request.POST:
            return self.post_servings(request)
        
        # Sprawdź, czy to formularz oceny (ma parametr rating)
        if 'rating' in request.POST and request.user.is_authenticated:
            return self.post_rating(request)
        
        # Jeśli to nie formularz zmiany porcji ani oceny, obsłuż dodawanie komentarzy
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
        
    def post_rating(self, request):
        """Obsługa formularza oceny przepisu"""
        try:
            # Pobierz istniejącą ocenę lub utwórz nową
            rating_obj, created = RecipeRating.objects.get_or_create(
                user=request.user,
                recipe=self.object,
                defaults={'rating': int(request.POST.get('rating'))}
            )
            
            # Jeśli ocena już istniała, zaktualizuj ją
            if not created:
                rating_obj.rating = int(request.POST.get('rating'))
                
            # Dodaj komentarz do oceny, jeśli został podany
            comment = request.POST.get('comment')
            if comment:
                rating_obj.comment = comment
            
            # Zapisz ocenę
            rating_obj.save()
            
            if created:
                messages.success(request, "Ocena została dodana.")
            else:
                messages.success(request, "Ocena została zaktualizowana.")
                
        except (ValueError, TypeError):
            messages.error(request, "Wystąpił błąd podczas zapisywania oceny.")
        
        return HttpResponseRedirect(self.object.get_absolute_url())
    
    def post_servings(self, request):
        """Obsługa formularza zmiany liczby porcji"""
        try:
            servings = int(request.POST.get('servings', 1))
            if servings <= 0:
                servings = 1
            
            # Przygotuj kontekst z uwzględnieniem przeskalowanej liczby porcji
            context = self.get_context_data(object=self.object)
            context['servings'] = servings
            context['original_servings'] = self.object.servings
            context['scaled_ingredients'] = self.object.scale_to_servings(servings)
            
            # Renderuj stronę z nowym kontekstem
            return self.render_to_response(context)
            
        except (ValueError, TypeError):
            # W przypadku nieprawidłowej wartości, przekieruj bez parametru
            return HttpResponseRedirect(self.object.get_absolute_url())

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
        
        # Dodaj puste dane składników jako JSON dla JavaScript (pusta tablica)
        context['ingredient_formset_data'] = '[]'
        
        return context
    
    def form_valid(self, form):
        print("\n[DEBUG] RecipeCreateView.form_valid - Kompleksowa przebudowa metody")
        
        # Najpierw sprawdzamy czy główny formularz jest poprawny
        if not form.is_valid():
            print("[DEBUG] Główny formularz zawiera błędy")
            return self.form_invalid(form)
            
        # Pobieramy formset składników
        context = self.get_context_data()
        ingredient_formset = context['ingredient_formset']
        print(f"[DEBUG] Otrzymano {len(ingredient_formset.forms)} formularzy składników")
        
        # Najpierw zapisujemy główny model przepisu
        recipe = form.save(commit=False)
        recipe.author = self.request.user
        recipe.save()
        print(f"[DEBUG] Zapisano główny przepis: {recipe.title} (ID: {recipe.id})")
        
        # Zapisujemy relacje many-to-many z głównego formularza
        form.save_m2m()
        
        # Teraz sprawdzamy czy formset jest poprawny
        if ingredient_formset.is_valid():
            print("[DEBUG] Formset składników jest poprawny")
            
            # Usuwamy istniejące składniki (jeśli to edycja)
            # W przypadku nowego przepisu to nie będzie miało efektu
            if recipe.id:
                print(f"[DEBUG] Usuwanie istniejących składników dla przepisu ID: {recipe.id}")
                RecipeIngredient.objects.filter(recipe=recipe).delete()
            
            # Teraz ręcznie tworzymy nowe składniki
            for ingredient_form in ingredient_formset:
                if ingredient_form.is_valid() and ingredient_form.has_changed() and not ingredient_form.cleaned_data.get('DELETE', False):
                    ingredient_data = ingredient_form.cleaned_data
                    ingredient = ingredient_data.get('ingredient')
                    amount = ingredient_data.get('amount')
                    unit = ingredient_data.get('unit')
                    
                    if ingredient and amount and unit:
                        # Sprawdź i dodaj kompatybilność jednostki jeśli potrzeba
                        if unit not in ingredient.compatible_units.all() and unit in ingredient.get_allowed_units():
                            print(f"[DEBUG] Dodawanie jednostki {unit.name} do kompatybilnych dla {ingredient.name}")
                            ingredient.compatible_units.add(unit)
                        
                        # Ręczne tworzenie obiektu składnika przepisu
                        print(f"[DEBUG] Tworzenie składnika: {ingredient.name}, {amount} {unit.symbol}")
                        RecipeIngredient.objects.create(
                            recipe=recipe,
                            ingredient=ingredient,
                            amount=amount,
                            unit=unit
                        )
            
            # Wyświetl komunikat sukcesu
            messages.success(self.request, f'Przepis "{recipe.title}" został pomyślnie zapisany.')
            
            # Ustaw obiekt do użycia w get_success_url
            self.object = recipe
            
            # Przekieruj do strony sukcesu
            return redirect(self.get_success_url())
        else:
            # Jeśli formset jest niepoprawny, wyświetl błędy i wróć do formularza
            print("[DEBUG] Formset składników zawiera błędy:")
            for i, form_errors in enumerate(ingredient_formset.errors):
                if form_errors:
                    print(f"[DEBUG] Błędy formularza {i}:", form_errors)
            
            # Jako że już zapisaliśmy przepis, ale formset jest niepoprawny,
            # usuwamy niedokończony przepis aby uniknąć śmieci w bazie danych
            recipe.delete()
            print(f"[DEBUG] Usunięto niedokończony przepis: {recipe.title}")
            
            messages.error(self.request, 'Formularz zawiera błędy. Sprawdź podane informacje o składnikach.')
            return self.form_invalid(form)
    
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
        
        # Dodaj dane składników jako JSON dla JavaScript
        ingredients_data = []
        for form in context['ingredient_formset'].forms:
            if hasattr(form.instance, 'pk') and form.instance.pk and form.instance.ingredient and form.instance.unit:
                ingredients_data.append({
                    'id': form.instance.pk,
                    'formIndex': context['ingredient_formset'].forms.index(form),
                    'ingredientId': form.instance.ingredient.id,
                    'ingredientName': form.instance.ingredient.name,
                    'amount': float(form.instance.amount),
                    'unitId': form.instance.unit.id,
                    'unitName': form.instance.unit.name,
                    'unitSymbol': form.instance.unit.symbol
                })
                
        context['ingredient_formset_data'] = json.dumps(ingredients_data)
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        ingredient_formset = context['ingredient_formset']
        
        # Sprawdź, czy formset jest prawidłowy lub czy jest pusty (brak składników)
        if ingredient_formset.is_valid():
            self.object = form.save()
            ingredient_formset.instance = self.object
            
            # Zapisz składniki tylko jeśli istnieją w formularzu
            ingredient_forms = ingredient_formset.save(commit=False)
            
            # Usuń składniki oznaczone do usunięcia
            for obj in ingredient_formset.deleted_objects:
                obj.delete()
            
            # Zapisz nowe i zaktualizowane składniki
            for ingredient_form in ingredient_forms:
                # Sprawdź, czy składnik nie jest pusty (czy ma wszystkie wymagane pola)
                if ingredient_form.ingredient and ingredient_form.amount and ingredient_form.unit:
                    ingredient_form.recipe = self.object
                    ingredient_form.save()
            
            messages.success(self.request, 'Przepis został zaktualizowany!')
            return redirect(self.get_success_url())
        else:
            # Jeśli formularz składników jest nieprawidłowy, pokaż błędy tylko jeśli formset zawiera jakieś dane
            has_non_empty_ingredients = False
            
            try:
                for form_data in ingredient_formset.cleaned_data:
                    # Jeśli którykolwiek z formularzy ma dane (nie jest pusty), sprawdź błędy
                    if form_data and any(form_data.values()):
                        has_non_empty_ingredients = True
                        break
            except AttributeError:
                # Obsługa przypadku, gdy formset nie ma atrybutu cleaned_data
                # Sprawdź, czy którykolwiek z formularzy ma dane
                for form in ingredient_formset.forms:
                    if form.has_changed():
                        has_non_empty_ingredients = True
                        break
            
            if has_non_empty_ingredients:
                for error in ingredient_formset.errors:
                    messages.error(self.request, f"Błąd składnika: {error}")
                for error in ingredient_formset.non_form_errors():
                    messages.error(self.request, f"Ogólny błąd: {error}")
                    
                return self.render_to_response(self.get_context_data(form=form))
            else:
                # Jeśli wszystkie formularze są puste, zapisz przepis bez składników
                self.object = form.save()
                
                messages.success(self.request, 'Przepis został zaktualizowany. Pamiętaj, aby dodać składniki!')
                return redirect(self.get_success_url())
    
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
            if servings <= 0:
                servings = recipe.servings
        except (ValueError, TypeError):
            servings = recipe.servings
    else:
        servings = recipe.servings
    
    # Sprawdź dostępność składników w lodówce
    missing_ingredients = recipe.get_missing_ingredients(request.user)
    
    # Przygotuj skalowane składniki, jeśli podano liczbę porcji
    scaled_ingredients = None
    scaled_missing_ingredients = None
    if servings and servings != recipe.servings:
        scaled_ingredients = recipe.scale_to_servings(servings)
        
        # Sprawdź dostępność składników dla przeskalowanych wartości
        scaled_missing_ingredients = []
        
        for scaled_ing in scaled_ingredients:
            ingredient = scaled_ing['ingredient']
            amount = scaled_ing['amount']
            unit = scaled_ing['unit']
            
            if not FridgeItem.check_ingredient_availability(request.user, ingredient, amount, unit):
                # Oblicz brakującą ilość
                total_available = 0.0
                fridge_items = FridgeItem.objects.filter(user=request.user, ingredient=ingredient)
                
                for item in fridge_items:
                    try:
                        # Jeśli jednostki są różne, przelicz
                        if item.unit != unit:
                            converted = convert_units(float(item.amount), item.unit, unit)
                            total_available += converted
                        else:
                            total_available += float(item.amount)
                    except Exception:
                        continue
                
                # Oblicz brakującą ilość
                missing_amount = max(0, float(amount) - total_available)
                
                scaled_missing_ingredients.append({
                    'ingredient': ingredient,
                    'unit': unit,
                    'required': float(amount),
                    'available': total_available,
                    'missing': missing_amount
                })
    
    if request.method == 'POST':
        post_servings = request.POST.get('servings')
        
        try:
            post_servings = int(post_servings)
            if post_servings <= 0:
                post_servings = recipe.servings
        except (ValueError, TypeError):
            post_servings = recipe.servings
            
        # Sprawdź dostępność składników jeszcze raz - uwzględniając aktualną liczbę porcji
        if post_servings != recipe.servings:
            # Jeśli liczba porcji jest inna niż domyślna, używamy specjalnego sprawdzenia
            scaled_ingredients = recipe.scale_to_servings(post_servings)
            current_missing_ingredients = []
            
            for scaled_ing in scaled_ingredients:
                ingredient = scaled_ing['ingredient']
                amount = scaled_ing['amount']
                unit = scaled_ing['unit']
                
                if not FridgeItem.check_ingredient_availability(request.user, ingredient, amount, unit):
                    current_missing_ingredients.append({
                        'ingredient': ingredient,
                        'amount': amount,
                        'unit': unit
                    })
        else:
            # Standardowe sprawdzenie dla domyślnej liczby porcji
            current_missing_ingredients = recipe.get_missing_ingredients(request.user)
            
        # Sprawdź czy wszystkie składniki są dostępne
        if current_missing_ingredients:
            if post_servings != recipe.servings:
                ingredient_names = [item['ingredient'].name for item in current_missing_ingredients]
            else:
                ingredient_names = [ing.ingredient.name for ing in current_missing_ingredients]
            
            missing_text = ", ".join(ingredient_names)
            
            messages.warning(
                request, 
                f'Nie możesz przygotować tego przepisu - brakuje składników: {missing_text}'
            )
            
            # Przekieruj do formularza dodawania brakujących składników do listy zakupów
            return redirect('recipes:add_missing_to_shopping_list', pk=recipe.pk)
        
        # Usuń składniki z lodówki
        try:
            from accounts.models import RecipeHistory
            
            # Jeśli liczba porcji jest inna niż domyślna, musimy użyć przeskalowanych składników
            if post_servings != recipe.servings:
                # Użyj przeskalowanych ilości składników
                success = True
                used_items = []
                scaled_ingredients = recipe.scale_to_servings(post_servings)
                
                for scaled_ing in scaled_ingredients:
                    ingredient = scaled_ing['ingredient']
                    amount = scaled_ing['amount']
                    unit = scaled_ing['unit']
                    
                    # Usuń składnik z lodówki
                    if not FridgeItem.remove_from_fridge(request.user, ingredient, amount, unit):
                        success = False
                        break
                    
                    used_items.append({
                        "ingredient": ingredient,
                        "amount": amount,
                        "unit": unit
                    })
                
                result = {
                    "success": success,
                    "used": used_items
                }
            else:
                # Standardowe usunięcie składników dla domyślnej liczby porcji
                result = FridgeItem.use_recipe_ingredients(request.user, recipe, post_servings)
            
            if result['success']:
                # Dodaj przepis do historii
                RecipeHistory.add_to_history(
                    user=request.user,
                    recipe=recipe,
                    servings=post_servings
                )
                
                # Przekaż informację o sukcesie przez sesję (do wyświetlenia modala)
                request.session['recipe_prepared'] = {
                    'recipe_id': recipe.pk,
                    'recipe_title': recipe.title,
                    'servings': post_servings,
                    'timestamp': timezone.now().strftime('%d.%m.%Y %H:%M')
                }
                
                messages.success(
                    request, 
                    f'Przygotowałeś przepis "{recipe.title}" ({post_servings} porcji). '
                    f'Składniki zostały usunięte z lodówki.'
                )
                return redirect('recipes:detail', pk=recipe.pk)
            else:
                # Jeśli nie udało się usunąć składników, pokaż informację o brakujących
                missing_text = ", ".join([item['ingredient'].name for item in result['missing']])
                messages.warning(
                    request, 
                    f'Nie możesz przygotować tego przepisu - brakuje składników: {missing_text}'
                )
                
                # Przekieruj do formularza dodawania brakujących składników do listy zakupów
                return redirect('recipes:add_missing_to_shopping_list', pk=recipe.pk)
        except Exception as e:
            messages.error(request, f'Wystąpił błąd podczas przygotowywania przepisu: {str(e)}')
            return redirect('recipes:detail', pk=recipe.pk)
    
    context = {
        'recipe': recipe,
        'servings': servings,
        'scaled_ingredients': scaled_ingredients,
        'scaled_missing_ingredients': scaled_missing_ingredients,
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
@require_POST
def clear_prepared_recipe(request):
    """Usuwa informację o przygotowanym przepisie z sesji"""
    if 'recipe_prepared' in request.session:
        del request.session['recipe_prepared']
    return JsonResponse({'success': True})

@login_required
def recipe_history(request):
    """Wyświetla historię przygotowanych przepisów"""
    from accounts.models import RecipeHistory
    
    history = RecipeHistory.objects.filter(user=request.user).select_related('recipe').order_by('-prepared_at')
    
    # Grupowanie po miesiącach
    from collections import defaultdict
    from django.utils.dateformat import DateFormat
    
    grouped_history = defaultdict(list)
    
    for item in history:
        # Klucz dla grupowania - miesiąc i rok (np. "Kwiecień 2023")
        date_format = DateFormat(item.prepared_at)
        month_key = f"{date_format.format('F')} {date_format.format('Y')}"
        grouped_history[month_key].append(item)
    
    context = {
        'history': dict(grouped_history),
        'history_count': history.count()
    }
    
    return render(request, 'recipes/recipe_history.html', context)

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
        base_amount = float(unit.base_ratio) * amount
        
        if unit.type == 'weight':
            # Dla wagi, pokaż konwersję na gramy/kilogramy
            if base_amount < 1000:
                conversion = f"{amount} {unit.symbol} = {base_amount:.2f} g"
            else:
                conversion = f"{amount} {unit.symbol} = {base_amount/1000:.2f} kg ({base_amount:.0f} g)"
        elif unit.type == 'volume':
            # Dla objętości, pokaż konwersję na ml/litry
            if base_amount < 1000:
                conversion = f"{amount} {unit.symbol} = {base_amount:.2f} ml"
            else:
                conversion = f"{amount} {unit.symbol} = {base_amount/1000:.2f} l ({base_amount:.0f} ml)"
        elif unit.type == 'piece':
            # Dla sztuk, nie pokazujemy domyślnie konwersji
            conversion = f"{amount} {unit.symbol}"
        elif unit.type == 'spoon':
            # Dla łyżek, pokaż konwersję na ml
            conversion = f"{amount} {unit.symbol} = {base_amount:.2f} ml"
            
        # Dodatkowe konwersje dla często używanych jednostek kuchennych
        additional_conversions = []
        
        # Dla objętości, dodaj konwersje na miary kuchenne
        if unit.type == 'volume' and unit.symbol == 'ml':
            if base_amount >= 15 and base_amount < 250:
                # Konwersja na łyżki
                tablespoons = base_amount / 15
                additional_conversions.append(f"≈ {tablespoons:.1f} łyżk{'' if tablespoons == 1 else 'i'}")
            
            if base_amount >= 5 and base_amount < 15:
                # Konwersja na łyżeczki
                teaspoons = base_amount / 5
                additional_conversions.append(f"≈ {teaspoons:.1f} łyżeczk{'' if teaspoons == 1 else 'i'}")
            
            if base_amount >= 250:
                # Konwersja na szklanki
                cups = base_amount / 250
                additional_conversions.append(f"≈ {cups:.1f} szklank{'' if cups == 1 else ('i' if cups < 5 else 'i')}")
        
        # Dla wagi, dodaj konwersje na łyżki/łyżeczki/szklanki (dla produktów sypkich)
        if unit.type == 'weight' and unit.symbol == 'g':
            if base_amount >= 15 and base_amount < 200:
                # Konwersja na łyżki (przybliżona)
                tablespoons = base_amount / 15
                additional_conversions.append(f"≈ {tablespoons:.1f} łyżk{'' if tablespoons == 1 else 'i'} (dla produktów sypkich)")
            
            if base_amount >= 5 and base_amount < 15:
                # Konwersja na łyżeczki (przybliżona)
                teaspoons = base_amount / 5
                additional_conversions.append(f"≈ {teaspoons:.1f} łyżeczk{'' if teaspoons == 1 else 'i'} (dla produktów sypkich)")
            
            if base_amount >= 200:
                # Konwersja na szklanki (przybliżona)
                cups = base_amount / 200
                additional_conversions.append(f"≈ {cups:.1f} szklank{'' if cups == 1 else ('i' if cups < 5 else 'i')} (dla produktów sypkich)")
        
        # Dodaj dodatkowe konwersje do głównej konwersji
        if additional_conversions:
            conversion += " (" + ", ".join(additional_conversions) + ")"
        
        return JsonResponse({
            'description': description,
            'conversion': conversion,
            'base_amount': base_amount,
            'unit_type': unit.type,
            'unit_symbol': unit.symbol,
            'requires_whole_number': unit.type == 'piece' or unit.symbol in ['szt', 'sztuka', 'garść', 'opakowanie']
        })
    except Exception as e:
        return JsonResponse({
            'description': '',
            'conversion': '',
            'error': str(e)
        }, status=400)

@login_required
def conversion_tables_list(request):
    """Przekierowanie do zgłaszania nowego składnika"""
    return redirect('recipes:submit_ingredient')

@login_required
def add_conversion_table(request):
    """Tworzenie nowej tablicy konwersji"""
    from django.forms import formset_factory
    
    ConversionEntryFormSet = formset_factory(ConversionEntryForm, extra=3)
    
    if request.method == 'POST':
        table_form = ConversionTableForm(request.POST)
        entry_formset = ConversionEntryFormSet(request.POST, prefix='entries')
        
        if table_form.is_valid() and entry_formset.is_valid():
            # Najpierw zapisz tablicę
            table = table_form.save(commit=False)
            table.created_by = request.user
            table.is_approved = False  # Nowe tablice wymagają zatwierdzenia
            table.save()
            
            # Potem zapisz wpisy konwersji
            for form in entry_formset:
                if form.cleaned_data and 'from_unit' in form.cleaned_data and 'to_unit' in form.cleaned_data:
                    entry = form.save(commit=False)
                    entry.table = table
                    entry.save()
            
            messages.success(request, 'Tablica konwersji została utworzona i oczekuje na zatwierdzenie przez administratora.')
            return redirect('recipes:conversion_tables')
    else:
        table_form = ConversionTableForm()
        entry_formset = ConversionEntryFormSet(prefix='entries')
    
    return render(request, 'recipes/add_conversion_table.html', {
        'table_form': table_form,
        'entry_formset': entry_formset,
        'measurement_units': MeasurementUnit.objects.all().order_by('type', 'name')
    })

@login_required
def conversion_table_detail(request, table_id):
    """Szczegóły tablicy konwersji"""
    table = get_object_or_404(ConversionTable, id=table_id)
    
    # Sprawdź uprawnienia - tylko zatwierdzone lub własne tablice
    if not table.is_approved and table.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'Nie masz uprawnień do wyświetlenia tej tablicy konwersji.')
        return redirect('recipes:conversion_tables')
    
    # Pobierz wszystkie wpisy dla tej tablicy
    entries = table.entries.all().order_by('from_unit__type', 'from_unit__name', 'to_unit__name')
    
    # Pogrupuj wpisy według typów jednostek
    grouped_entries = {}
    for entry in entries:
        unit_type = entry.from_unit.type
        if unit_type not in grouped_entries:
            grouped_entries[unit_type] = []
        grouped_entries[unit_type].append(entry)
    
    return render(request, 'recipes/conversion_table_detail.html', {
        'table': table,
        'grouped_entries': grouped_entries
    })

@login_required
def submit_ingredient(request):
    """Zgłoszenie nowego składnika przez użytkownika"""
    from django import forms
    
    class UserIngredientForm(forms.ModelForm):
        class Meta:
            model = UserIngredient
            fields = ['name', 'category', 'description', 'piece_weight', 'conversion_table']
            widgets = {
                'description': forms.Textarea(attrs={'rows': 3}),
            }
            labels = {
                'piece_weight': 'Średnia waga sztuki',
                'conversion_table': 'Tablica konwersji',
            }
            help_texts = {
                'piece_weight': 'Opcjonalne - podaj jeśli wiesz ile waży jedna sztuka składnika (w gramach)',
                'conversion_table': 'Wybierz odpowiednią tablicę konwersji dla tego składnika',
            }
    
    if request.method == 'POST':
        form = UserIngredientForm(request.POST)
        if form.is_valid():
            ingredient = form.save(commit=False)
            ingredient.user = request.user
            ingredient.status = 'pending'
            
            # Podstawowe parametry
            conversion_table = form.cleaned_data.get('conversion_table')
            ingredient.conversion_table = conversion_table
            
            # Ustaw domyślną jednostkę i typ jednostek na podstawie tablicy konwersji
            if conversion_table:
                # Znajdź domyślną jednostkę na podstawie product_type
                default_unit = None
                unit_type = 'weight_volume'  # domyślnie
                
                if 'Płyny' in conversion_table.product_type:
                    # Dla płynów, ustaw domyślną jednostkę ml
                    try:
                        default_unit = MeasurementUnit.objects.get(symbol='ml')
                        unit_type = 'volume_spoon'
                    except MeasurementUnit.DoesNotExist:
                        pass
                elif ingredient.piece_weight:
                    # Jeśli podano wagę sztuki, prawdopodobnie to produkt liczony w sztukach
                    try:
                        default_unit = MeasurementUnit.objects.get(symbol='szt')
                        unit_type = 'weight_piece'
                    except MeasurementUnit.DoesNotExist:
                        pass
                else:
                    # Dla innych produktów, ustaw domyślną jednostkę g
                    try:
                        default_unit = MeasurementUnit.objects.get(symbol='g')
                        unit_type = 'weight_volume'
                    except MeasurementUnit.DoesNotExist:
                        pass
                
                ingredient.default_unit = default_unit
                ingredient.unit_type = unit_type
            else:
                # Brak tablicy konwersji - ustaw domyślne wartości
                ingredient.default_unit = None
                ingredient.unit_type = 'weight_volume'  # domyślny typ jednostek
            
            ingredient.density = None  # domyślnie brak gęstości
            ingredient.save()
            
            messages.success(request, f'Składnik "{ingredient.name}" został zgłoszony i oczekuje na zatwierdzenie przez administratora.')
            return redirect('recipes:my_submissions')
        else:
            # Jeśli formularz zawiera błędy, pokaż je użytkownikowi
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Błąd w polu {field}: {error}")
    else:
        form = UserIngredientForm()
    
    # Pobierz tablice konwersji pogrupowane według kategorii
    conversion_tables = ConversionTable.objects.filter(is_approved=True).order_by('category__name', 'name')
    grouped_tables = []
    
    # Grupuję według kategorii produktów
    categories = IngredientCategory.objects.all()
    for category in categories:
        tables = conversion_tables.filter(category=category)
        if tables.exists():
            grouped_tables.append({
                'category_name': category.name,
                'tables': list(tables)
            })
    
    return render(request, 'recipes/submit_ingredient.html', {
        'form': form,
        'grouped_tables': grouped_tables
    })

@login_required
def my_ingredient_submissions(request):
    """Lista składników zgłoszonych przez użytkownika"""
    submissions = UserIngredient.objects.filter(user=request.user).order_by('-submitted_at')
    
    # Podział na strony
    paginator = Paginator(submissions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'recipes/my_ingredient_submissions.html', {
        'page_obj': page_obj
    })

# Funkcja pomocnicza do sprawdzania uprawnień administratora
def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@user_passes_test(is_admin)
def admin_pending_ingredients(request):
    """Panel administratora - składniki oczekujące na zatwierdzenie"""
    pending = UserIngredient.objects.filter(status='pending').order_by('-submitted_at')
    recent = UserIngredient.objects.exclude(status='pending').order_by('-submitted_at')[:10]
    
    # Pobierz wszystkie zatwierdzone tablice konwersji
    conversion_tables = ConversionTable.objects.filter(is_approved=True).order_by('category__name', 'name')
    
    # Pogrupowane jednostki miary
    measurement_units = MeasurementUnit.objects.all().order_by('type', 'name')
    grouped_units = []
    
    from itertools import groupby
    for unit_type, units in groupby(measurement_units, key=lambda x: x.get_type_display()):
        grouped_units.append({
            'grouper': unit_type,
            'list': list(units)
        })
    
    # Lista typów jednostek
    unit_types = UserIngredient._meta.get_field('unit_type').choices
    
    return render(request, 'recipes/admin/pending_ingredients.html', {
        'pending_ingredients': pending,
        'recent_ingredients': recent,
        'conversion_tables': conversion_tables,
        'measurement_units': grouped_units,
        'unit_types': unit_types
    })

@user_passes_test(is_admin)
def admin_approve_ingredient(request, ingredient_id):
    """Zatwierdzenie składnika przez administratora"""
    user_ingredient = get_object_or_404(UserIngredient, id=ingredient_id, status='pending')
    
    if request.method == 'POST':
        try:
            # Pobierz parametry z formularza
            conversion_table_id = request.POST.get('conversion_table')
            default_unit_id = request.POST.get('default_unit')
            unit_type = request.POST.get('unit_type')
            density = request.POST.get('density')
            piece_weight = request.POST.get('piece_weight')
            admin_comment = request.POST.get('admin_comment', '')
            
            # Sprawdź czy wymagane pola są wypełnione
            if not conversion_table_id or not default_unit_id or not unit_type:
                messages.error(request, 'Musisz wypełnić wszystkie wymagane pola, aby zatwierdzić składnik.')
                return redirect('recipes:admin_pending_ingredients')
            
            # Sprawdź czy piece_weight jest wymagane dla unit_type z piece
            if 'piece' in unit_type.lower() and not piece_weight:
                messages.error(request, 'Dla składnika mierzonego w sztukach musisz podać wagę sztuki (piece_weight).')
                return redirect('recipes:admin_pending_ingredients')
            
            # Przypisz wartości do składnika
            user_ingredient.conversion_table = get_object_or_404(ConversionTable, id=conversion_table_id)
            user_ingredient.default_unit = get_object_or_404(MeasurementUnit, id=default_unit_id)
            user_ingredient.unit_type = unit_type
            
            # Przypisz gęstość jeśli podana (opcjonalna)
            if density:
                try:
                    user_ingredient.density = float(density)
                except ValueError:
                    user_ingredient.density = None
            
            # Przypisz wagę sztuki jeśli podana
            if piece_weight:
                try:
                    user_ingredient.piece_weight = float(piece_weight)
                except ValueError:
                    user_ingredient.piece_weight = None
            
            # Dodaj komentarz administratora jeśli podany
            if admin_comment:
                user_ingredient.admin_notes = admin_comment
                
            # Zapisz zmiany przed wywołaniem metody approve
            user_ingredient.save()
            
            # Zatwierdź składnik
            ingredient = user_ingredient.approve(admin_user=request.user)
            messages.success(request, f'Składnik "{ingredient.name}" został zatwierdzony i dodany do bazy.')
            
        except Exception as e:
            messages.error(request, f'Błąd podczas zatwierdzania składnika: {str(e)}')
    
    return redirect('recipes:admin_pending_ingredients')

@user_passes_test(is_admin)
def admin_reject_ingredient(request, ingredient_id):
    """Odrzucenie składnika przez administratora"""
    user_ingredient = get_object_or_404(UserIngredient, id=ingredient_id, status='pending')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        try:
            user_ingredient.reject(reason=reason, admin_user=request.user)
            messages.success(request, f'Składnik "{user_ingredient.name}" został odrzucony.')
        except Exception as e:
            messages.error(request, f'Błąd podczas odrzucania składnika: {str(e)}')
    
    return redirect('recipes:admin_pending_ingredients')

def ajax_ingredient_details(request):
    """Widok AJAX do pobierania szczegółów składnika"""
    ingredient_id = request.GET.get('ingredient_id')
    
    if not ingredient_id:
        return JsonResponse({
            'success': False,
            'error': 'Brak ID składnika'
        })
    
    try:
        ingredient = get_object_or_404(Ingredient, id=ingredient_id)
        
        # Przygotuj dane o składniku
        data = {
            'id': ingredient.id,
            'name': ingredient.name,
            'category': ingredient.category.name if ingredient.category else None,
            'unit_type': ingredient.get_unit_type_display(),
            'default_unit': ingredient.default_unit.name if ingredient.default_unit else None,
            'density': float(ingredient.density) if ingredient.density else None,
            'piece_weight': float(ingredient.piece_weight) if ingredient.piece_weight else None,
            'success': True
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def ajax_search_suggestions(request):
    """Widok AJAX do pobierania sugestii wyszukiwania"""
    query = request.GET.get('q', '')
    
    # Jeśli zapytanie jest puste, zwróć pusty wynik
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Pobierz tytuły przepisów pasujące do zapytania
    suggestions = Recipe.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(ingredients__ingredient__name__icontains=query)
    ).distinct().values_list('title', flat=True)[:10]
    
    return JsonResponse({'suggestions': list(suggestions)}) 

def ajax_load_units_by_type(request):
    unit_type = request.GET.get('unit_type')
    units = []
    
    if unit_type:
        if unit_type == 'weight_only':
            units = MeasurementUnit.objects.filter(type='weight')
        elif unit_type == 'volume_only':
            units = MeasurementUnit.objects.filter(type='volume')
        elif unit_type == 'piece_only':
            units = MeasurementUnit.objects.filter(type='piece')
        elif unit_type == 'spoon_only':
            units = MeasurementUnit.objects.filter(type='spoon')
        elif unit_type == 'weight_volume':
            units = MeasurementUnit.objects.filter(type__in=['weight', 'volume'])
        elif unit_type == 'weight_piece':
            units = MeasurementUnit.objects.filter(type__in=['weight', 'piece'])
        elif unit_type == 'weight_spoon':
            units = MeasurementUnit.objects.filter(type__in=['weight', 'spoon'])
        elif unit_type == 'volume_spoon':
            units = MeasurementUnit.objects.filter(type__in=['volume', 'spoon'])
        elif unit_type == 'all':
            units = MeasurementUnit.objects.all()
    
    return JsonResponse({
        'units': [{'id': unit.id, 'name': f"{unit.name} ({unit.symbol})"} for unit in units]
    })

@login_required
@require_POST
def toggle_rating_helpful(request, pk):
    """Przełącza oznaczenie oceny jako przydatna"""
    rating = get_object_or_404(RecipeRating, pk=pk)
    
    # Przełącz oznaczenie oceny jako przydatna
    is_helpful = rating.toggle_helpful(request.user)
    
    # Jeśli to żądanie AJAX, zwróć odpowiedź JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'is_helpful': is_helpful,
            'helpful_count': rating.helpful_count
        })
    
    # W przeciwnym razie, przekieruj z powrotem do strony przepisu
    return HttpResponseRedirect(rating.recipe.get_absolute_url())

# Widoki administratora do zarządzania jednostkami miary

@user_passes_test(is_admin)
def admin_units_list(request):
    """Panel administratora - lista jednostek miary"""
    units = MeasurementUnit.objects.all().order_by('type', 'name')
    
    # Grupowanie jednostek według typu
    grouped_units = []
    from itertools import groupby
    for unit_type, units_group in groupby(units, key=lambda x: x.get_type_display()):
        grouped_units.append({
            'type': unit_type,
            'units': list(units_group)
        })
    
    return render(request, 'recipes/admin/units_list.html', {
        'grouped_units': grouped_units
    })

@user_passes_test(is_admin)
def admin_unit_create(request):
    """Panel administratora - tworzenie nowej jednostki miary"""
    if request.method == 'POST':
        # Pobierz dane z formularza
        name = request.POST.get('name')
        symbol = request.POST.get('symbol')
        unit_type = request.POST.get('type')
        base_ratio = request.POST.get('base_ratio')
        is_common = request.POST.get('is_common') == 'on'
        description = request.POST.get('description', '')
        
        # Walidacja danych
        errors = []
        if not name:
            errors.append('Nazwa jest wymagana')
        if not symbol:
            errors.append('Symbol jest wymagany')
        if not unit_type:
            errors.append('Typ jednostki jest wymagany')
        if not base_ratio:
            errors.append('Przelicznik bazowy jest wymagany')
        
        # Sprawdź, czy jednostka o podanym symbolu już istnieje
        if MeasurementUnit.objects.filter(symbol=symbol).exists():
            errors.append(f'Jednostka o symbolu "{symbol}" już istnieje')
        
        if not errors:
            try:
                # Utwórz nową jednostkę
                unit = MeasurementUnit.objects.create(
                    name=name,
                    symbol=symbol,
                    type=unit_type,
                    base_ratio=base_ratio,
                    is_common=is_common,
                    description=description
                )
                messages.success(request, f'Jednostka "{unit.name}" została utworzona')
                return redirect('recipes:admin_units_list')
            except Exception as e:
                errors.append(f'Błąd podczas tworzenia jednostki: {str(e)}')
        
        # Wyświetl błędy walidacji
        for error in errors:
            messages.error(request, error)
    
    # Przygotuj dane do formularza
    unit_types = MeasurementUnit._meta.get_field('type').choices
    
    return render(request, 'recipes/admin/unit_form.html', {
        'unit_types': unit_types,
        'is_new': True
    })

@user_passes_test(is_admin)
def admin_unit_edit(request, pk):
    """Panel administratora - edycja jednostki miary"""
    unit = get_object_or_404(MeasurementUnit, pk=pk)
    
    if request.method == 'POST':
        # Pobierz dane z formularza
        name = request.POST.get('name')
        symbol = request.POST.get('symbol')
        unit_type = request.POST.get('type')
        base_ratio = request.POST.get('base_ratio')
        is_common = request.POST.get('is_common') == 'on'
        description = request.POST.get('description', '')
        
        # Walidacja danych
        errors = []
        if not name:
            errors.append('Nazwa jest wymagana')
        if not symbol:
            errors.append('Symbol jest wymagany')
        if not unit_type:
            errors.append('Typ jednostki jest wymagany')
        if not base_ratio:
            errors.append('Przelicznik bazowy jest wymagany')
        
        # Sprawdź, czy jednostka o podanym symbolu już istnieje (z pominięciem obecnej jednostki)
        if MeasurementUnit.objects.filter(symbol=symbol).exclude(pk=pk).exists():
            errors.append(f'Jednostka o symbolu "{symbol}" już istnieje')
        
        if not errors:
            try:
                # Zaktualizuj jednostkę
                unit.name = name
                unit.symbol = symbol
                unit.type = unit_type
                unit.base_ratio = base_ratio
                unit.is_common = is_common
                unit.description = description
                unit.save()
                
                messages.success(request, f'Jednostka "{unit.name}" została zaktualizowana')
                return redirect('recipes:admin_units_list')
            except Exception as e:
                errors.append(f'Błąd podczas aktualizacji jednostki: {str(e)}')
        
        # Wyświetl błędy walidacji
        for error in errors:
            messages.error(request, error)
    
    # Przygotuj dane do formularza
    unit_types = MeasurementUnit._meta.get_field('type').choices
    
    return render(request, 'recipes/admin/unit_form.html', {
        'unit': unit,
        'unit_types': unit_types,
        'is_new': False
    })

@user_passes_test(is_admin)
def admin_unit_delete(request, pk):
    """Panel administratora - usuwanie jednostki miary"""
    unit = get_object_or_404(MeasurementUnit, pk=pk)
    
    if request.method == 'POST':
        try:
            unit_name = unit.name
            unit.delete()
            messages.success(request, f'Jednostka "{unit_name}" została usunięta')
        except Exception as e:
            messages.error(request, f'Błąd podczas usuwania jednostki: {str(e)}')
        
        return redirect('recipes:admin_units_list')
    
    return render(request, 'recipes/admin/unit_confirm_delete.html', {
        'unit': unit
    })

# Widoki administratora do zarządzania kategoriami składników

@user_passes_test(is_admin)
def admin_categories_list(request):
    """Panel administratora - lista kategorii składników"""
    categories = IngredientCategory.objects.all().order_by('name')
    
    return render(request, 'recipes/admin/categories_list.html', {
        'categories': categories
    })

@user_passes_test(is_admin)
def admin_category_create(request):
    """Panel administratora - tworzenie nowej kategorii składników"""
    if request.method == 'POST':
        # Pobierz dane z formularza
        name = request.POST.get('name')
        is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        is_vegan = request.POST.get('is_vegan') == 'on'
        
        # Walidacja danych
        errors = []
        if not name:
            errors.append('Nazwa jest wymagana')
        
        # Sprawdź, czy kategoria o podanej nazwie już istnieje
        if IngredientCategory.objects.filter(name=name).exists():
            errors.append(f'Kategoria o nazwie "{name}" już istnieje')
        
        if not errors:
            try:
                # Utwórz nową kategorię
                category = IngredientCategory.objects.create(
                    name=name,
                    is_vegetarian=is_vegetarian,
                    is_vegan=is_vegan
                )
                messages.success(request, f'Kategoria "{category.name}" została utworzona')
                return redirect('recipes:admin_categories_list')
            except Exception as e:
                errors.append(f'Błąd podczas tworzenia kategorii: {str(e)}')
        
        # Wyświetl błędy walidacji
        for error in errors:
            messages.error(request, error)
    
    return render(request, 'recipes/admin/category_form.html', {
        'is_new': True
    })

@user_passes_test(is_admin)
def admin_category_edit(request, pk):
    """Panel administratora - edycja kategorii składników"""
    category = get_object_or_404(IngredientCategory, pk=pk)
    
    if request.method == 'POST':
        # Pobierz dane z formularza
        name = request.POST.get('name')
        is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        is_vegan = request.POST.get('is_vegan') == 'on'
        
        # Walidacja danych
        errors = []
        if not name:
            errors.append('Nazwa jest wymagana')
        
        # Sprawdź, czy kategoria o podanej nazwie już istnieje (z pominięciem obecnej kategorii)
        if IngredientCategory.objects.filter(name=name).exclude(pk=pk).exists():
            errors.append(f'Kategoria o nazwie "{name}" już istnieje')
        
        if not errors:
            try:
                # Zaktualizuj kategorię
                category.name = name
                category.is_vegetarian = is_vegetarian
                category.is_vegan = is_vegan
                category.save()
                
                messages.success(request, f'Kategoria "{category.name}" została zaktualizowana')
                return redirect('recipes:admin_categories_list')
            except Exception as e:
                errors.append(f'Błąd podczas aktualizacji kategorii: {str(e)}')
        
        # Wyświetl błędy walidacji
        for error in errors:
            messages.error(request, error)
    
    return render(request, 'recipes/admin/category_form.html', {
        'category': category,
        'is_new': False
    })

@user_passes_test(is_admin)
def admin_category_delete(request, pk):
    """Panel administratora - usuwanie kategorii składników"""
    category = get_object_or_404(IngredientCategory, pk=pk)
    
    # Sprawdź czy istnieją składniki przypisane do tej kategorii
    ingredients_count = Ingredient.objects.filter(category=category).count()
    
    if request.method == 'POST':
        try:
            category_name = category.name
            category.delete()
            messages.success(request, f'Kategoria "{category_name}" została usunięta')
        except Exception as e:
            messages.error(request, f'Błąd podczas usuwania kategorii: {str(e)}')
        
        return redirect('recipes:admin_categories_list')
    
    return render(request, 'recipes/admin/category_confirm_delete.html', {
        'category': category,
        'ingredients_count': ingredients_count
    })

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Panel główny administratora"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Pobierz dane statystyczne
    users_count = User.objects.count()
    recipes_count = Recipe.objects.count()
    ingredients_count = Ingredient.objects.count()
    pending_ingredients_count = UserIngredient.objects.filter(status='pending').count()
    
    return render(request, 'admin/admin_dashboard.html', {
        'users_count': users_count,
        'recipes_count': recipes_count,
        'ingredients_count': ingredients_count,
        'pending_ingredients_count': pending_ingredients_count
    })

@user_passes_test(is_admin)
def admin_statistics(request):
    """Panel statystyk aplikacji"""
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Avg
    from django.utils import timezone
    import datetime
    
    User = get_user_model()
    
    # Statystyki ogólne
    users_count = User.objects.count()
    recipes_count = Recipe.objects.count()
    ingredients_count = Ingredient.objects.count()
    
    # Statystyki przepisów
    avg_rating = Recipe.objects.aggregate(avg=Avg('reciperating__rating'))['avg'] or 0
    avg_rating = round(avg_rating, 1)
    
    # Najlepiej oceniane przepisy
    top_recipes = Recipe.objects.annotate(
        avg_rating=Avg('reciperating__rating'),
        ratings_count=Count('reciperating')
    ).filter(ratings_count__gt=0).order_by('-avg_rating')[:5]
    
    # Najpopularniejsze przepisy (po liczbie polubień)
    popular_recipes = Recipe.objects.annotate(
        likes_count=Count('likes')
    ).order_by('-likes_count')[:5]
    
    # Aktywność w czasie
    # Liczba nowych przepisów w ostatnich 6 miesiącach
    today = timezone.now().date()
    six_months_ago = today - datetime.timedelta(days=180)
    
    # Przygotuj dane dla wykresu
    months_labels = []
    recipes_data = []
    
    for i in range(6):
        month_date = today - datetime.timedelta(days=30 * i)
        month_start = datetime.date(month_date.year, month_date.month, 1)
        if month_date.month == 12:
            next_month = 1
            next_year = month_date.year + 1
        else:
            next_month = month_date.month + 1
            next_year = month_date.year
            
        month_end = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)
        
        # Pobierz liczbę przepisów dla tego miesiąca
        month_recipes = Recipe.objects.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        ).count()
        
        # Dodaj dane do list
        months_labels.insert(0, month_date.strftime('%b %Y'))
        recipes_data.insert(0, month_recipes)
    
    return render(request, 'admin/admin_statistics.html', {
        'users_count': users_count,
        'recipes_count': recipes_count,
        'ingredients_count': ingredients_count,
        'avg_rating': avg_rating,
        'top_recipes': top_recipes,
        'popular_recipes': popular_recipes,
        'months_labels': months_labels,
        'recipes_data': recipes_data
    })

@user_passes_test(is_admin)
def admin_import_export(request):
    """Panel importu/eksportu danych"""
    
    if request.method == 'POST':
        # Obsługa eksportu
        if 'export_units' in request.POST:
            # Eksport jednostek miary do CSV
            response = HttpResponse(
                content_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename="measurement_units.csv"'},
            )
            
            writer = csv.writer(response)
            writer.writerow(['name', 'symbol', 'type', 'base_ratio', 'is_common', 'description'])
            
            units = MeasurementUnit.objects.all()
            for unit in units:
                writer.writerow([
                    unit.name,
                    unit.symbol,
                    unit.type,
                    unit.base_ratio,
                    unit.is_common,
                    unit.description or ''
                ])
            
            messages.success(request, 'Jednostki miary zostały wyeksportowane.')
            return response
            
        elif 'export_categories' in request.POST:
            # Eksport kategorii składników do CSV
            response = HttpResponse(
                content_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename="ingredient_categories.csv"'},
            )
            
            writer = csv.writer(response)
            writer.writerow(['name', 'description'])
            
            categories = IngredientCategory.objects.all()
            for category in categories:
                writer.writerow([
                    category.name,
                    category.description or ''
                ])
            
            messages.success(request, 'Kategorie składników zostały wyeksportowane.')
            return response
            
        elif 'export_ingredients' in request.POST:
            # Eksport składników do CSV
            response = HttpResponse(
                content_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename="ingredients.csv"'},
            )
            
            writer = csv.writer(response)
            writer.writerow(['name', 'category', 'unit_type', 'default_unit', 'piece_weight', 'density', 'description'])
            
            ingredients = Ingredient.objects.all()
            for ingredient in ingredients:
                writer.writerow([
                    ingredient.name,
                    ingredient.category.name if ingredient.category else '',
                    ingredient.unit_type,
                    ingredient.default_unit.symbol if ingredient.default_unit else '',
                    ingredient.piece_weight or '',
                    ingredient.density or '',
                    ingredient.description or ''
                ])
            
            messages.success(request, 'Składniki zostały wyeksportowane.')
            return response
            
        # Obsługa importu
        elif 'import_units' in request.POST:
            if 'units_file' in request.FILES:
                csv_file = request.FILES['units_file']
                
                if not csv_file.name.endswith('.csv'):
                    messages.error(request, 'Proszę wgrać plik CSV.')
                    return redirect('recipes:admin_import_export')
                
                try:
                    decoded_file = csv_file.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(decoded_file)
                    
                    for row in reader:
                        MeasurementUnit.objects.update_or_create(
                            name=row['name'],
                            defaults={
                                'symbol': row['symbol'],
                                'type': row['type'],
                                'base_ratio': float(row['base_ratio']),
                                'is_common': row['is_common'].lower() in ('true', 't', 'yes', 'y', '1'),
                                'description': row['description']
                            }
                        )
                    
                    messages.success(request, 'Jednostki miary zostały zaimportowane.')
                except Exception as e:
                    messages.error(request, f'Wystąpił błąd podczas importu: {str(e)}')
            else:
                messages.error(request, 'Nie wybrano pliku.')
                
            return redirect('recipes:admin_import_export')
            
        elif 'import_categories' in request.POST:
            if 'categories_file' in request.FILES:
                csv_file = request.FILES['categories_file']
                
                if not csv_file.name.endswith('.csv'):
                    messages.error(request, 'Proszę wgrać plik CSV.')
                    return redirect('recipes:admin_import_export')
                
                try:
                    decoded_file = csv_file.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(decoded_file)
                    
                    for row in reader:
                        IngredientCategory.objects.update_or_create(
                            name=row['name'],
                            defaults={
                                'description': row['description']
                            }
                        )
                    
                    messages.success(request, 'Kategorie składników zostały zaimportowane.')
                except Exception as e:
                    messages.error(request, f'Wystąpił błąd podczas importu: {str(e)}')
            else:
                messages.error(request, 'Nie wybrano pliku.')
                
            return redirect('recipes:admin_import_export')
            
        elif 'import_ingredients' in request.POST:
            if 'ingredients_file' in request.FILES:
                csv_file = request.FILES['ingredients_file']
                
                if not csv_file.name.endswith('.csv'):
                    messages.error(request, 'Proszę wgrać plik CSV.')
                    return redirect('recipes:admin_import_export')
                
                try:
                    decoded_file = csv_file.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(decoded_file)
                    
                    imported_count = 0
                    error_count = 0
                    
                    for row in reader:
                        try:
                            # Znajdź kategorię
                            category = None
                            if row['category']:
                                category, _ = IngredientCategory.objects.get_or_create(name=row['category'])
                            
                            # Znajdź domyślną jednostkę
                            default_unit = None
                            if row['default_unit']:
                                try:
                                    default_unit = MeasurementUnit.objects.get(symbol=row['default_unit'])
                                except MeasurementUnit.DoesNotExist:
                                    pass
                            
                            # Przygotuj wartości liczbowe
                            piece_weight = None
                            if row.get('piece_weight') and row['piece_weight'].strip():
                                try:
                                    piece_weight = float(row['piece_weight'])
                                except (ValueError, TypeError):
                                    pass
                            
                            density = None
                            if row.get('density') and row['density'].strip():
                                try:
                                    density = float(row['density'])
                                except (ValueError, TypeError):
                                    pass
                            
                            # Utwórz lub zaktualizuj składnik
                            ingredient, created = Ingredient.objects.update_or_create(
                                name=row['name'],
                                defaults={
                                    'category': category,
                                    'unit_type': row['unit_type'] if row.get('unit_type') else 'weight_volume',
                                    'default_unit': default_unit,
                                    'piece_weight': piece_weight,
                                    'density': density,
                                    'description': row.get('description', '')
                                }
                            )
                            
                            imported_count += 1
                        except Exception as e:
                            error_count += 1
                    
                    if error_count > 0:
                        messages.warning(request, f'Zaimportowano {imported_count} składników. Wystąpiło {error_count} błędów.')
                    else:
                        messages.success(request, f'Zaimportowano {imported_count} składników.')
                        
                except Exception as e:
                    messages.error(request, f'Wystąpił błąd podczas importu: {str(e)}')
            else:
                messages.error(request, 'Nie wybrano pliku.')
                
            return redirect('recipes:admin_import_export')
    
    # Przekierowanie do widoku
    context = {
        'title': 'Import/Export danych',
        'measurements_count': MeasurementUnit.objects.count(),
        'categories_count': IngredientCategory.objects.count(),
        'ingredients_count': Ingredient.objects.count(),
        'unread_notifications_count': unread_notifications_count(request),
    }
    return render(request, 'recipes/admin/import_export.html', context)