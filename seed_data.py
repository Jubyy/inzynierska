"""
Skrypt do tworzenia przykładowych danych w aplikacji książki kucharskiej.
Uruchom go z konsoli Django:

python manage.py shell
>>> from seed_data import seed_database
>>> seed_database()
"""

import random
import datetime
from django.utils import timezone
from django.contrib.auth.models import User

from recipes.models import Ingredient, Recipe, RecipeIngredient, MeasurementUnit, RecipeCategory, IngredientCategory
from accounts.models import UserProfile, UserFollowing
from fridge.models import FridgeItem
from shopping.models import ShoppingList, ShoppingItem

def create_measurement_units():
    """Tworzy podstawowe jednostki miary"""
    print("Tworzenie jednostek miary...")
    
    # Jednostki wagowe
    weight_units = [
        {'name': 'Gram', 'symbol': 'g', 'type': 'weight', 'base_ratio': 1.0, 'is_common': True},
        {'name': 'Kilogram', 'symbol': 'kg', 'type': 'weight', 'base_ratio': 1000.0, 'is_common': True},
        {'name': 'Dekagram', 'symbol': 'dag', 'type': 'weight', 'base_ratio': 10.0, 'is_common': True},
    ]
    
    # Jednostki objętości
    volume_units = [
        {'name': 'Mililitr', 'symbol': 'ml', 'type': 'volume', 'base_ratio': 1.0, 'is_common': True},
        {'name': 'Litr', 'symbol': 'l', 'type': 'volume', 'base_ratio': 1000.0, 'is_common': True},
    ]
    
    # Jednostki łyżkowe
    spoon_units = [
        {'name': 'Łyżeczka', 'symbol': 'łyżeczka', 'type': 'spoon', 'base_ratio': 5.0, 'is_common': True},
        {'name': 'Łyżka', 'symbol': 'łyżka', 'type': 'spoon', 'base_ratio': 15.0, 'is_common': True},
        {'name': 'Szklanka', 'symbol': 'szklanka', 'type': 'volume', 'base_ratio': 250.0, 'is_common': True, 'description': 'szklanka 250ml'},
    ]
    
    # Inne jednostki
    other_units = [
        {'name': 'Sztuka', 'symbol': 'szt', 'type': 'count', 'base_ratio': 1.0, 'is_common': True},
        {'name': 'Szczypta', 'symbol': 'szczypta', 'type': 'other', 'base_ratio': 0.5, 'is_common': True},
        {'name': 'Garść', 'symbol': 'garść', 'type': 'other', 'base_ratio': 30.0, 'is_common': True},
    ]
    
    units = weight_units + volume_units + spoon_units + other_units
    
    # Tworzenie jednostek
    created_units = {}
    for unit_data in units:
        unit, created = MeasurementUnit.objects.get_or_create(
            symbol=unit_data['symbol'],
            defaults=unit_data
        )
        created_units[unit.symbol] = unit
        if created:
            print(f"Utworzono jednostkę: {unit.name} ({unit.symbol})")
        else:
            print(f"Jednostka {unit.name} już istnieje")
    
    return created_units

def create_ingredient_categories():
    """Tworzy kategorie składników"""
    print("Tworzenie kategorii składników...")
    
    categories = [
        {'name': 'Owoce', 'is_vegetarian': True, 'is_vegan': True},
        {'name': 'Warzywa', 'is_vegetarian': True, 'is_vegan': True},
        {'name': 'Mięso', 'is_vegetarian': False, 'is_vegan': False},
        {'name': 'Nabiał', 'is_vegetarian': True, 'is_vegan': False},
        {'name': 'Pieczywo', 'is_vegetarian': True, 'is_vegan': True},
        {'name': 'Przyprawy', 'is_vegetarian': True, 'is_vegan': True},
        {'name': 'Produkty zbożowe', 'is_vegetarian': True, 'is_vegan': True},
        {'name': 'Tłuszcze', 'is_vegetarian': True, 'is_vegan': False},
        {'name': 'Orzechy i nasiona', 'is_vegetarian': True, 'is_vegan': True},
        {'name': 'Napoje', 'is_vegetarian': True, 'is_vegan': True}
    ]
    
    # Tworzenie kategorii
    created_categories = {}
    for cat_data in categories:
        category, created = IngredientCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        created_categories[category.name] = category
        if created:
            print(f"Utworzono kategorię: {category.name}")
        else:
            print(f"Kategoria {category.name} już istnieje")
    
    return created_categories

def create_ingredients(categories, units):
    """Tworzy przykładowe składniki"""
    print("Tworzenie składników...")
    
    ingredients_data = [
        # Owoce
        {'name': 'Jabłko', 'category': 'Owoce', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 150},
        {'name': 'Banan', 'category': 'Owoce', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 120},
        {'name': 'Truskawki', 'category': 'Owoce', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Maliny', 'category': 'Owoce', 'default_unit': 'g', 'unit_type': 'weight_only'},
        
        # Warzywa
        {'name': 'Marchew', 'category': 'Warzywa', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 80},
        {'name': 'Ziemniak', 'category': 'Warzywa', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 100},
        {'name': 'Cebula', 'category': 'Warzywa', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 75},
        {'name': 'Czosnek', 'category': 'Warzywa', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 5},
        {'name': 'Pomidor', 'category': 'Warzywa', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 120},
        
        # Mięso
        {'name': 'Pierś z kurczaka', 'category': 'Mięso', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Mięso mielone wołowe', 'category': 'Mięso', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Filet z łososia', 'category': 'Mięso', 'default_unit': 'g', 'unit_type': 'weight_only'},
        
        # Nabiał
        {'name': 'Mleko', 'category': 'Nabiał', 'default_unit': 'ml', 'unit_type': 'volume_only', 'density': 1.03},
        {'name': 'Jajko', 'category': 'Nabiał', 'default_unit': 'szt', 'unit_type': 'piece_only', 'piece_weight': 60},
        {'name': 'Ser żółty', 'category': 'Nabiał', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Jogurt naturalny', 'category': 'Nabiał', 'default_unit': 'g', 'unit_type': 'weight_volume', 'density': 1.05},
        
        # Pieczywo
        {'name': 'Chleb pszenny', 'category': 'Pieczywo', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Bułka', 'category': 'Pieczywo', 'default_unit': 'szt', 'unit_type': 'weight_piece', 'piece_weight': 50},
        
        # Przyprawy
        {'name': 'Sól', 'category': 'Przyprawy', 'default_unit': 'g', 'unit_type': 'weight_spoon'},
        {'name': 'Pieprz czarny', 'category': 'Przyprawy', 'default_unit': 'g', 'unit_type': 'weight_spoon'},
        {'name': 'Bazylia', 'category': 'Przyprawy', 'default_unit': 'g', 'unit_type': 'weight_spoon'},
        {'name': 'Oregano', 'category': 'Przyprawy', 'default_unit': 'g', 'unit_type': 'weight_spoon'},
        
        # Produkty zbożowe
        {'name': 'Ryż biały', 'category': 'Produkty zbożowe', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Makaron spaghetti', 'category': 'Produkty zbożowe', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Kasza gryczana', 'category': 'Produkty zbożowe', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Mąka pszenna', 'category': 'Produkty zbożowe', 'default_unit': 'g', 'unit_type': 'weight_only'},
        
        # Tłuszcze
        {'name': 'Olej rzepakowy', 'category': 'Tłuszcze', 'default_unit': 'ml', 'unit_type': 'volume_only', 'density': 0.92},
        {'name': 'Masło', 'category': 'Tłuszcze', 'default_unit': 'g', 'unit_type': 'weight_only'},
        {'name': 'Oliwa z oliwek', 'category': 'Tłuszcze', 'default_unit': 'ml', 'unit_type': 'volume_only', 'density': 0.92},
    ]
    
    # Tworzenie składników
    created_ingredients = {}
    for ing_data in ingredients_data:
        # Pobierz kategorię i jednostkę
        category = categories.get(ing_data['category'])
        default_unit = units.get(ing_data['default_unit'])
        
        if not category or not default_unit:
            print(f"Pominięto składnik {ing_data['name']} - brak kategorii lub jednostki")
            continue
        
        # Usuwamy kcal_per_100g, ponieważ nie ma takiego pola w modelu
        defaults = {
            'category': category,
            'default_unit': default_unit,
            'unit_type': ing_data['unit_type'],
        }
        
        # Dodajemy opcjonalne pola tylko jeśli są obecne w danych
        if 'piece_weight' in ing_data:
            defaults['piece_weight'] = ing_data['piece_weight']
        if 'density' in ing_data:
            defaults['density'] = ing_data['density']
        if 'description' in ing_data:
            defaults['description'] = ing_data['description']
        
        ingredient, created = Ingredient.objects.get_or_create(
            name=ing_data['name'],
            defaults=defaults
        )
        
        # Dodaj kompatybilne jednostki
        if ing_data['unit_type'] == 'weight_only' or ing_data['unit_type'] == 'weight_piece' or ing_data['unit_type'] == 'weight_spoon' or ing_data['unit_type'] == 'weight_volume':
            for symbol in ['g', 'kg', 'dag']:
                if symbol in units:
                    ingredient.compatible_units.add(units[symbol])
        
        if ing_data['unit_type'] == 'volume_only' or ing_data['unit_type'] == 'volume_spoon' or ing_data['unit_type'] == 'weight_volume':
            for symbol in ['ml', 'l', 'szklanka']:
                if symbol in units:
                    ingredient.compatible_units.add(units[symbol])
        
        if ing_data['unit_type'] == 'weight_spoon' or ing_data['unit_type'] == 'volume_spoon':
            for symbol in ['łyżka', 'łyżeczka']:
                if symbol in units:
                    ingredient.compatible_units.add(units[symbol])
        
        created_ingredients[ingredient.name] = ingredient
        if created:
            print(f"Utworzono składnik: {ingredient.name}")
        else:
            print(f"Składnik {ingredient.name} już istnieje")
    
    return created_ingredients

def create_recipe_categories():
    """Tworzy kategorie przepisów"""
    print("Tworzenie kategorii przepisów...")
    
    categories = [
        {'name': 'Śniadania', 'description': 'Przepisy na śniadania'},
        {'name': 'Obiady', 'description': 'Przepisy na obiady'},
        {'name': 'Kolacje', 'description': 'Przepisy na kolacje'},
        {'name': 'Desery', 'description': 'Słodkości i desery'},
        {'name': 'Zupy', 'description': 'Różne rodzaje zup'},
        {'name': 'Sałatki', 'description': 'Przepisy na sałatki'},
        {'name': 'Napoje', 'description': 'Koktajle, napoje, drinki'},
        {'name': 'Wegetariańskie', 'description': 'Przepisy dla wegetarian'},
        {'name': 'Wegańskie', 'description': 'Przepisy dla wegan'},
        {'name': 'Kuchnia Polska', 'description': 'Tradycyjne polskie przepisy'},
    ]
    
    created_categories = {}
    for cat_data in categories:
        category, created = RecipeCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        created_categories[category.name] = category
        if created:
            print(f"Utworzono kategorię przepisów: {category.name}")
        else:
            print(f"Kategoria przepisów {category.name} już istnieje")
    
    return created_categories

def create_users():
    """Tworzy przykładowych użytkowników"""
    print("Tworzenie użytkowników...")
    
    users_data = [
        {'username': 'testuser', 'email': 'test@example.com', 'password': 'testpassword', 'first_name': 'Test', 'last_name': 'User'},
        {'username': 'jankowalski', 'email': 'jan@example.com', 'password': 'testpassword', 'first_name': 'Jan', 'last_name': 'Kowalski'},
        {'username': 'annanowak', 'email': 'anna@example.com', 'password': 'testpassword', 'first_name': 'Anna', 'last_name': 'Nowak'},
        {'username': 'marcinwojcik', 'email': 'marcin@example.com', 'password': 'testpassword', 'first_name': 'Marcin', 'last_name': 'Wójcik'},
        {'username': 'katarzynakowalczyk', 'email': 'katarzyna@example.com', 'password': 'testpassword', 'first_name': 'Katarzyna', 'last_name': 'Kowalczyk'},
    ]
    
    created_users = {}
    for user_data in users_data:
        try:
            user = User.objects.get(username=user_data['username'])
            print(f"Użytkownik {user.username} już istnieje")
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name']
            )
            print(f"Utworzono użytkownika: {user.username}")
        
        # Zaktualizuj profil użytkownika
        profile = user.profile
        if not profile.bio:
            profile.bio = f"Profil użytkownika {user.username}. Lubię gotować i eksperymentować w kuchni."
            profile.favorite_cuisine = random.choice(['Polska', 'Włoska', 'Azjatycka', 'Meksykańska', 'Francuska'])
            profile.save()
        
        created_users[user.username] = user
    
    # Dodaj relacje obserwowania między użytkownikami
    if 'jankowalski' in created_users and 'annanowak' in created_users:
        UserFollowing.objects.get_or_create(
            user=created_users['jankowalski'],
            followed_user=created_users['annanowak']
        )
    
    if 'annanowak' in created_users and 'marcinwojcik' in created_users:
        UserFollowing.objects.get_or_create(
            user=created_users['annanowak'],
            followed_user=created_users['marcinwojcik']
        )
    
    if 'testuser' in created_users and 'jankowalski' in created_users:
        UserFollowing.objects.get_or_create(
            user=created_users['testuser'],
            followed_user=created_users['jankowalski']
        )
    
    return created_users

def create_recipes(users, recipe_categories, ingredients, units):
    """Tworzy przykładowe przepisy"""
    print("Tworzenie przepisów...")
    
    recipes_data = [
        {
            'title': 'Spaghetti Bolognese',
            'description': 'Klasyczne włoskie danie z makaronem i sosem mięsnym.',
            'author': 'jankowalski',
            'categories': ['Obiady', 'Kuchnia Polska'],
            'preparation_time': 45,
            'servings': 4,
            'difficulty': 'MEDIUM',
            'instructions': """
1. W dużym garnku rozgrzej olej i zeszklij posiekaną cebulę.
2. Dodaj czosnek i smaż przez 30 sekund.
3. Dodaj mięso mielone i smaż, aż będzie brązowe, rozdrabniając je widelcem.
4. Dodaj pomidory, sól, pieprz i zioła. Gotuj na małym ogniu przez 20 minut.
5. W tym czasie ugotuj makaron zgodnie z instrukcją na opakowaniu.
6. Podawaj sos na makaronie, posypany startym serem.""",
            'is_public': True,
            'ingredients': [
                {'ingredient': 'Makaron spaghetti', 'amount': 400, 'unit': 'g'},
                {'ingredient': 'Mięso mielone wołowe', 'amount': 500, 'unit': 'g'},
                {'ingredient': 'Cebula', 'amount': 1, 'unit': 'szt'},
                {'ingredient': 'Czosnek', 'amount': 2, 'unit': 'szt'},
                {'ingredient': 'Pomidor', 'amount': 4, 'unit': 'szt'},
                {'ingredient': 'Olej rzepakowy', 'amount': 2, 'unit': 'łyżka'},
                {'ingredient': 'Sól', 'amount': 1, 'unit': 'szczypta'},
                {'ingredient': 'Pieprz czarny', 'amount': 1, 'unit': 'szczypta'},
                {'ingredient': 'Bazylia', 'amount': 1, 'unit': 'łyżka'},
                {'ingredient': 'Oregano', 'amount': 1, 'unit': 'łyżeczka'},
                {'ingredient': 'Ser żółty', 'amount': 100, 'unit': 'g'},
            ]
        },
        {
            'title': 'Sałatka grecka',
            'description': 'Lekka sałatka z pomidorami, ogórkiem, oliwkami i serem feta.',
            'author': 'annanowak',
            'categories': ['Sałatki', 'Wegetariańskie'],
            'preparation_time': 15,
            'servings': 2,
            'difficulty': 'EASY',
            'instructions': """
1. Pokrój pomidory i ogórki w kostkę.
2. Pokrój ser feta w kostkę.
3. Wymieszaj wszystkie składniki w misce.
4. Skrop oliwą z oliwek, dopraw solą i pieprzem.
5. Posyp oregano i podawaj.""",
            'is_public': True,
            'ingredients': [
                {'ingredient': 'Pomidor', 'amount': 2, 'unit': 'szt'},
                {'ingredient': 'Cebula', 'amount': 0.5, 'unit': 'szt'},
                {'ingredient': 'Oliwa z oliwek', 'amount': 2, 'unit': 'łyżka'},
                {'ingredient': 'Sól', 'amount': 1, 'unit': 'szczypta'},
                {'ingredient': 'Pieprz czarny', 'amount': 1, 'unit': 'szczypta'},
                {'ingredient': 'Oregano', 'amount': 1, 'unit': 'łyżeczka'},
            ]
        },
        {
            'title': 'Omlet z warzywami',
            'description': 'Puszysty omlet z dodatkiem warzyw, idealny na śniadanie.',
            'author': 'marcinwojcik',
            'categories': ['Śniadania', 'Wegetariańskie'],
            'preparation_time': 15,
            'servings': 1,
            'difficulty': 'EASY',
            'instructions': """
1. Roztrzep jajka w misce, dodaj sól i pieprz.
2. Pokrój pomidora i cebulę w kostkę.
3. Rozgrzej patelnię z odrobiną masła.
4. Wlej masę jajeczną na patelnię.
5. Gdy omlet zacznie się ścinać, dodaj warzywa.
6. Złóż omlet na pół i podawaj.""",
            'is_public': True,
            'ingredients': [
                {'ingredient': 'Jajko', 'amount': 3, 'unit': 'szt'},
                {'ingredient': 'Pomidor', 'amount': 1, 'unit': 'szt'},
                {'ingredient': 'Cebula', 'amount': 0.5, 'unit': 'szt'},
                {'ingredient': 'Masło', 'amount': 1, 'unit': 'łyżka'},
                {'ingredient': 'Sól', 'amount': 1, 'unit': 'szczypta'},
                {'ingredient': 'Pieprz czarny', 'amount': 1, 'unit': 'szczypta'},
            ]
        },
        {
            'title': 'Koktajl owocowy',
            'description': 'Orzeźwiający koktajl z bananami i truskawkami.',
            'author': 'katarzynakowalczyk',
            'categories': ['Napoje', 'Wegetariańskie', 'Wegańskie'],
            'preparation_time': 5,
            'servings': 2,
            'difficulty': 'EASY',
            'instructions': """
1. Obierz banana i pokrój go na kawałki.
2. Umyj truskawki i odetnij szypułki.
3. Umieść wszystkie składniki w blenderze.
4. Miksuj do uzyskania gładkiej konsystencji.
5. Przelej do szklanek i podawaj natychmiast.""",
            'is_public': True,
            'ingredients': [
                {'ingredient': 'Banan', 'amount': 1, 'unit': 'szt'},
                {'ingredient': 'Truskawki', 'amount': 200, 'unit': 'g'},
                {'ingredient': 'Mleko', 'amount': 200, 'unit': 'ml'},
                {'ingredient': 'Jogurt naturalny', 'amount': 100, 'unit': 'g'},
            ]
        },
        {
            'title': 'Ryż z warzywami',
            'description': 'Proste i sycące danie z ryżem i warzywami.',
            'author': 'testuser',
            'categories': ['Obiady', 'Wegetariańskie', 'Wegańskie'],
            'preparation_time': 30,
            'servings': 2,
            'difficulty': 'EASY',
            'instructions': """
1. Ugotuj ryż zgodnie z instrukcją na opakowaniu.
2. Pokrój warzywa (marchewkę, cebulę) w kostkę.
3. Rozgrzej olej na patelni i zeszklij cebulę.
4. Dodaj marchewkę i smaż przez 5 minut.
5. Dodaj ugotowany ryż, dopraw solą i pieprzem.
6. Smażyć wszystko razem przez 2-3 minuty.""",
            'is_public': True,
            'ingredients': [
                {'ingredient': 'Ryż biały', 'amount': 200, 'unit': 'g'},
                {'ingredient': 'Marchew', 'amount': 2, 'unit': 'szt'},
                {'ingredient': 'Cebula', 'amount': 1, 'unit': 'szt'},
                {'ingredient': 'Olej rzepakowy', 'amount': 2, 'unit': 'łyżka'},
                {'ingredient': 'Sól', 'amount': 1, 'unit': 'szczypta'},
                {'ingredient': 'Pieprz czarny', 'amount': 1, 'unit': 'szczypta'},
            ]
        },
    ]
    
    created_recipes = []
    for recipe_data in recipes_data:
        # Pobierz autora i kategorie
        author = users.get(recipe_data['author'])
        if not author:
            print(f"Pominięto przepis {recipe_data['title']} - brak autora")
            continue
        
        # Sprawdź, czy przepis już istnieje
        existing_recipe = Recipe.objects.filter(title=recipe_data['title'], author=author).first()
        if existing_recipe:
            print(f"Przepis {recipe_data['title']} już istnieje")
            continue
        
        # Utwórz przepis
        recipe = Recipe.objects.create(
            title=recipe_data['title'],
            description=recipe_data['description'],
            author=author,
            preparation_time=recipe_data['preparation_time'],
            servings=recipe_data['servings'],
            difficulty=recipe_data['difficulty'],
            instructions=recipe_data['instructions'],
            is_public=recipe_data['is_public']
        )
        
        # Dodaj kategorie
        for cat_name in recipe_data['categories']:
            if cat_name in recipe_categories:
                recipe.categories.add(recipe_categories[cat_name])
        
        # Dodaj składniki
        for ing_data in recipe_data['ingredients']:
            ingredient = ingredients.get(ing_data['ingredient'])
            unit = units.get(ing_data['unit'])
            
            if ingredient and unit:
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient,
                    amount=ing_data['amount'],
                    unit=unit
                )
        
        created_recipes.append(recipe)
        print(f"Utworzono przepis: {recipe.title}")
    
    return created_recipes

def add_items_to_fridge(users, ingredients, units):
    """Dodaje przykładowe produkty do lodówki"""
    print("Dodawanie produktów do lodówki...")
    
    # Dla każdego użytkownika dodaj kilka produktów
    items_data = [
        # Dla testuser
        {'user': 'testuser', 'ingredient': 'Mleko', 'amount': 1000, 'unit': 'ml', 'days': 5},
        {'user': 'testuser', 'ingredient': 'Jajko', 'amount': 10, 'unit': 'szt', 'days': 14},
        {'user': 'testuser', 'ingredient': 'Masło', 'amount': 200, 'unit': 'g', 'days': 30},
        {'user': 'testuser', 'ingredient': 'Chleb pszenny', 'amount': 1, 'unit': 'szt', 'days': 3},
        {'user': 'testuser', 'ingredient': 'Ser żółty', 'amount': 300, 'unit': 'g', 'days': 21},
        
        # Dla jankowalski
        {'user': 'jankowalski', 'ingredient': 'Pierś z kurczaka', 'amount': 500, 'unit': 'g', 'days': 2},
        {'user': 'jankowalski', 'ingredient': 'Makaron spaghetti', 'amount': 400, 'unit': 'g', 'days': 180},
        {'user': 'jankowalski', 'ingredient': 'Pomidor', 'amount': 4, 'unit': 'szt', 'days': 7},
        {'user': 'jankowalski', 'ingredient': 'Cebula', 'amount': 3, 'unit': 'szt', 'days': 14},
        {'user': 'jankowalski', 'ingredient': 'Marchew', 'amount': 5, 'unit': 'szt', 'days': 10},
        
        # Dla annanowak
        {'user': 'annanowak', 'ingredient': 'Jabłko', 'amount': 6, 'unit': 'szt', 'days': 14},
        {'user': 'annanowak', 'ingredient': 'Banan', 'amount': 4, 'unit': 'szt', 'days': 5},
        {'user': 'annanowak', 'ingredient': 'Jogurt naturalny', 'amount': 400, 'unit': 'g', 'days': 10},
        {'user': 'annanowak', 'ingredient': 'Mleko', 'amount': 1000, 'unit': 'ml', 'days': 7},
        {'user': 'annanowak', 'ingredient': 'Jajko', 'amount': 6, 'unit': 'szt', 'days': 21},
    ]
    
    for item_data in items_data:
        user = users.get(item_data['user'])
        ingredient = ingredients.get(item_data['ingredient'])
        unit = units.get(item_data['unit'])
        
        if not user or not ingredient or not unit:
            continue
        
        # Sprawdź, czy produkt już istnieje
        if FridgeItem.objects.filter(user=user, ingredient=ingredient).exists():
            print(f"Produkt {ingredient.name} już istnieje w lodówce użytkownika {user.username}")
            continue
        
        # Oblicz datę ważności
        expiry_date = timezone.now().date() + datetime.timedelta(days=item_data['days'])
        
        # Dodaj produkt do lodówki
        fridge_item = FridgeItem.objects.create(
            user=user,
            ingredient=ingredient,
            amount=item_data['amount'],
            unit=unit,
            expiry_date=expiry_date,
            purchase_date=timezone.now().date()
        )
        
        print(f"Dodano produkt {ingredient.name} do lodówki użytkownika {user.username}")
    
    return True

def create_shopping_lists(users, ingredients, units):
    """Tworzy przykładowe listy zakupów"""
    print("Tworzenie list zakupów...")
    
    lists_data = [
        {
            'user': 'testuser',
            'name': 'Zakupy weekendowe',
            'items': [
                {'ingredient': 'Jabłko', 'amount': 6, 'unit': 'szt'},
                {'ingredient': 'Chleb pszenny', 'amount': 2, 'unit': 'szt'},
                {'ingredient': 'Masło', 'amount': 200, 'unit': 'g'},
                {'ingredient': 'Mleko', 'amount': 2, 'unit': 'l'},
                {'ingredient': 'Jogurt naturalny', 'amount': 400, 'unit': 'g'},
            ]
        },
        {
            'user': 'jankowalski',
            'name': 'Składniki na obiad',
            'items': [
                {'ingredient': 'Pierś z kurczaka', 'amount': 500, 'unit': 'g'},
                {'ingredient': 'Ryż biały', 'amount': 400, 'unit': 'g'},
                {'ingredient': 'Marchew', 'amount': 4, 'unit': 'szt'},
                {'ingredient': 'Cebula', 'amount': 2, 'unit': 'szt'},
                {'ingredient': 'Czosnek', 'amount': 1, 'unit': 'szt'},
            ]
        },
        {
            'user': 'annanowak',
            'name': 'Koktajl na weekend',
            'items': [
                {'ingredient': 'Banan', 'amount': 3, 'unit': 'szt'},
                {'ingredient': 'Truskawki', 'amount': 500, 'unit': 'g'},
                {'ingredient': 'Jogurt naturalny', 'amount': 400, 'unit': 'g'},
            ]
        }
    ]
    
    for list_data in lists_data:
        user = users.get(list_data['user'])
        if not user:
            continue
        
        # Sprawdź, czy lista już istnieje
        if ShoppingList.objects.filter(user=user, name=list_data['name']).exists():
            print(f"Lista zakupów {list_data['name']} już istnieje dla użytkownika {user.username}")
            continue
        
        # Utwórz listę zakupów
        shopping_list = ShoppingList.objects.create(
            user=user,
            name=list_data['name'],
            created_at=timezone.now()
        )
        
        # Dodaj elementy do listy
        for item_data in list_data['items']:
            ingredient = ingredients.get(item_data['ingredient'])
            unit = units.get(item_data['unit'])
            
            if ingredient and unit:
                ShoppingItem.objects.create(
                    shopping_list=shopping_list,
                    ingredient=ingredient,
                    amount=item_data['amount'],
                    unit=unit,
                    is_purchased=random.choice([True, False])
                )
        
        print(f"Utworzono listę zakupów {shopping_list.name} dla użytkownika {user.username}")
    
    return True

def seed_database():
    """Główna funkcja do wypełniania bazy danych przykładowymi danymi"""
    print("Rozpoczęcie dodawania przykładowych danych...")
    
    # Tworzenie podstawowych danych
    units = create_measurement_units()
    ingredient_categories = create_ingredient_categories()
    ingredients = create_ingredients(ingredient_categories, units)
    recipe_categories = create_recipe_categories()
    users = create_users()
    
    # Tworzenie przepisów i innych danych
    recipes = create_recipes(users, recipe_categories, ingredients, units)
    add_items_to_fridge(users, ingredients, units)
    create_shopping_lists(users, ingredients, units)
    
    print("Zakończono dodawanie przykładowych danych!")
    
if __name__ == "__main__":
    seed_database() 