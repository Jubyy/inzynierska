import os
import sys
import django
import random
from django.utils import timezone

# Dodajemy ścieżkę projektu do sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ustawiamy zmienną środowiskową dla Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ksiazkakucharska.settings')
django.setup()

# Importujemy modele
from django.contrib.auth.models import User
from recipes.models import Recipe, RecipeCategory, Ingredient, RecipeIngredient, MeasurementUnit, IngredientCategory

def create_test_recipes():
    """Tworzy testowe przepisy do testowania funkcji filtrowania i sortowania"""
    print("Tworzenie testowych przepisów...")
    
    # Sprawdzamy, czy admin istnieje
    try:
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        print("Użytkownik 'admin' nie istnieje. Utwórz go najpierw używając 'python manage.py createsuperuser'.")
        return False
    
    # Utworzenie kategorii przepisów
    categories = [
        ('Zupy', 'Różne rodzaje zup'),
        ('Dania główne', 'Podstawowe dania obiadowe'),
        ('Desery', 'Słodkie wypieki i przekąski'),
        ('Śniadania', 'Potrawy na dobry początek dnia'),
        ('Przekąski', 'Małe przekąski i przystawki')
    ]
    
    category_objects = []
    for name, description in categories:
        cat, created = RecipeCategory.objects.get_or_create(
            name=name,
            defaults={'description': description}
        )
        category_objects.append(cat)
        if created:
            print(f"Utworzono kategorię przepisów: {name}")
        else:
            print(f"Kategoria przepisów {name} już istnieje")
    
    # Utworzenie kategorii składników
    ingredient_categories = [
        'Nabiał',
        'Mięso',
        'Warzywa',
        'Owoce',
        'Produkty zbożowe',
        'Przyprawy',
        'Płyny',
        'Dodatki'
    ]
    
    ingredient_category_objects = {}
    for name in ingredient_categories:
        cat, created = IngredientCategory.objects.get_or_create(
            name=name
        )
        ingredient_category_objects[name] = cat
        if created:
            print(f"Utworzono kategorię składników: {name}")
        else:
            print(f"Kategoria składników {name} już istnieje")
    
    # Przypisanie kategorii do składników
    ingredient_to_category = {
        'Mąka pszenna': 'Produkty zbożowe',
        'Cukier': 'Dodatki',
        'Sól': 'Przyprawy',
        'Mleko': 'Nabiał',
        'Jajka': 'Nabiał',
        'Masło': 'Nabiał',
        'Woda': 'Płyny',
        'Drożdże': 'Dodatki',
        'Ziemniaki': 'Warzywa',
        'Marchew': 'Warzywa',
        'Cebula': 'Warzywa',
        'Czosnek': 'Warzywa',
        'Pietruszka': 'Warzywa',
        'Seler': 'Warzywa',
        'Por': 'Warzywa',
        'Kurczak': 'Mięso',
        'Mięso mielone': 'Mięso',
        'Schab': 'Mięso',
        'Łopatka wieprzowa': 'Mięso',
        'Ryż': 'Produkty zbożowe',
        'Makaron': 'Produkty zbożowe',
        'Pomidory': 'Warzywa',
        'Ogórki': 'Warzywa',
        'Kapusta': 'Warzywa',
        'Papryka': 'Warzywa',
        'Grzyby': 'Warzywa',
        'Śmietana': 'Nabiał',
        'Twaróg': 'Nabiał',
        'Ser feta': 'Nabiał',
        'Olej': 'Płyny',
        'Oliwa z oliwek': 'Płyny',
        'Bułka tarta': 'Produkty zbożowe',
        'Oliwki czarne': 'Dodatki',
        'Szczypiorek': 'Przyprawy',
        'Cebula czerwona': 'Warzywa',
        'Proszek do pieczenia': 'Dodatki'
    }
    
    # Utworzenie jednostek miary
    units = [
        ('g', 'Gram', 'weight', 1.0),
        ('kg', 'Kilogram', 'weight', 1000.0),
        ('ml', 'Mililitr', 'volume', 1.0),
        ('l', 'Litr', 'volume', 1000.0),
        ('szt', 'Sztuka', 'piece', 1.0),
        ('łyżka', 'Łyżka', 'spoon', 15.0),
        ('łyżeczka', 'Łyżeczka', 'spoon', 5.0)
    ]
    
    unit_objects = {}
    for symbol, name, unit_type, base_ratio in units:
        unit, created = MeasurementUnit.objects.get_or_create(
            symbol=symbol,
            defaults={
                'name': name,
                'type': unit_type,
                'base_ratio': base_ratio,
                'is_common': True
            }
        )
        unit_objects[symbol] = unit
        if created:
            print(f"Utworzono jednostkę: {name}")
        else:
            print(f"Jednostka {name} już istnieje")
    
    # Utworzenie składników
    ingredients = [
        ('Mąka pszenna', 'Podstawowa mąka do wypieku ciast i chleba'),
        ('Cukier', 'Biały cukier'),
        ('Sól', 'Sól kuchenna'),
        ('Mleko', 'Mleko krowie 3.2%'),
        ('Jajka', 'Świeże jajka kurze'),
        ('Masło', 'Masło extra'),
        ('Woda', 'Woda'),
        ('Drożdże', 'Drożdże piekarskie'),
        ('Ziemniaki', 'Ziemniaki'),
        ('Marchew', 'Marchew'),
        ('Cebula', 'Cebula'),
        ('Czosnek', 'Czosnek'),
        ('Pietruszka', 'Pietruszka korzeń'),
        ('Seler', 'Seler korzeń'),
        ('Por', 'Por'),
        ('Kurczak', 'Filet z kurczaka'),
        ('Mięso mielone', 'Mięso mielone wieprzowo-wołowe'),
        ('Schab', 'Schab wieprzowy'),
        ('Ryż', 'Ryż biały'),
        ('Makaron', 'Makaron pszenny'),
        ('Pomidory', 'Pomidory'),
        ('Ogórki', 'Ogórki'),
        ('Kapusta', 'Kapusta biała'),
        ('Papryka', 'Papryka czerwona'),
        ('Grzyby', 'Pieczarki'),
        ('Śmietana', 'Śmietana 18%'),
        ('Twaróg', 'Twaróg półtłusty'),
        ('Ser feta', 'Ser feta w kostkach'),
        ('Olej', 'Olej roślinny'),
        ('Oliwa z oliwek', 'Oliwa z oliwek extra virgin'),
        ('Bułka tarta', 'Bułka tarta'),
        ('Oliwki czarne', 'Oliwki czarne drylowane'),
        ('Szczypiorek', 'Szczypiorek świeży'),
        ('Cebula czerwona', 'Cebula czerwona'),
        ('Proszek do pieczenia', 'Proszek do pieczenia'),
        ('Łopatka wieprzowa', 'Łopatka wieprzowa')
    ]
    
    ingredient_objects = {}
    for name, description in ingredients:
        # Pobierz kategorię dla składnika
        category_name = ingredient_to_category.get(name)
        if not category_name or category_name not in ingredient_category_objects:
            print(f"Brak kategorii dla składnika {name}, pomijam")
            continue
            
        category = ingredient_category_objects[category_name]
        
        ing, created = Ingredient.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
                'category': category
            }
        )
        ingredient_objects[name] = ing
        if created:
            print(f"Utworzono składnik: {name} (kategoria: {category_name})")
        else:
            print(f"Składnik {name} już istnieje")
    
    # Testowe przepisy
    recipes = [
        {
            'title': 'Zupa pomidorowa',
            'description': 'Klasyczna zupa pomidorowa z ryżem',
            'preparation_time': 45,
            'servings': 4,
            'difficulty': 'easy',
            'categories': ['Zupy'],
            'ingredients': [
                ('Pomidory', 500, 'g'),
                ('Marchew', 2, 'szt'),
                ('Cebula', 1, 'szt'),
                ('Czosnek', 2, 'szt'),
                ('Pietruszka', 1, 'szt'),
                ('Seler', 100, 'g'),
                ('Ryż', 100, 'g'),
                ('Woda', 2, 'l'),
                ('Śmietana', 100, 'ml'),
                ('Sól', 1, 'łyżeczka')
            ],
            'preparation': 'Warzywa umyć, obrać i pokroić. Gotować w wodzie przez 30 minut. Dodać pomidory i gotować jeszcze 15 minut. Zmiksować, dodać ugotowany ryż, zabielić śmietaną i doprawić solą.'
        },
        {
            'title': 'Kotlet schabowy',
            'description': 'Tradycyjny kotlet schabowy z ziemniakami i surówką',
            'preparation_time': 60,
            'servings': 4,
            'difficulty': 'medium',
            'categories': ['Dania główne'],
            'ingredients': [
                ('Schab', 600, 'g'),
                ('Jajka', 2, 'szt'),
                ('Mąka pszenna', 100, 'g'),
                ('Bułka tarta', 200, 'g'),
                ('Ziemniaki', 1, 'kg'),
                ('Kapusta', 300, 'g'),
                ('Marchew', 2, 'szt'),
                ('Sól', 2, 'łyżeczka'),
                ('Olej', 100, 'ml')
            ],
            'preparation': 'Schab pokroić na kotlety, rozbić, doprawić solą i pieprzem. Panierować w mące, jajku i bułce tartej. Smażyć na oleju. Ziemniaki obrać, ugotować i podawać z kotletem. Przygotować surówkę z kapusty i marchewki.'
        },
        {
            'title': 'Sernik',
            'description': 'Puszysty sernik na kruchym spodzie',
            'preparation_time': 120,
            'servings': 12,
            'difficulty': 'hard',
            'categories': ['Desery'],
            'ingredients': [
                ('Twaróg', 1, 'kg'),
                ('Jajka', 5, 'szt'),
                ('Mąka pszenna', 150, 'g'),
                ('Cukier', 250, 'g'),
                ('Masło', 200, 'g'),
                ('Śmietana', 200, 'ml')
            ],
            'preparation': 'Przygotować kruchy spód z mąki, masła i cukru. Ser zmiksować z jajkami, cukrem i śmietaną. Wylać na spód i piec 50 minut w 180 stopniach.'
        },
        {
            'title': 'Jajecznica',
            'description': 'Prosta jajecznica na maśle z dodatkami',
            'preparation_time': 15,
            'servings': 2,
            'difficulty': 'easy',
            'categories': ['Śniadania'],
            'ingredients': [
                ('Jajka', 4, 'szt'),
                ('Masło', 20, 'g'),
                ('Cebula', 1, 'szt'),
                ('Sól', 1, 'łyżeczka'),
                ('Szczypiorek', 1, 'łyżka')
            ],
            'preparation': 'Cebulę pokroić i zeszklić na maśle. Dodać roztrzepane jajka. Smażyć mieszając. Doprawić solą i posypać szczypiorkiem.'
        },
        {
            'title': 'Sałatka grecka',
            'description': 'Orzeźwiająca sałatka z serem feta i oliwkami',
            'preparation_time': 20,
            'servings': 4,
            'difficulty': 'easy',
            'categories': ['Przekąski'],
            'ingredients': [
                ('Pomidory', 4, 'szt'),
                ('Ogórki', 2, 'szt'),
                ('Cebula czerwona', 1, 'szt'),
                ('Ser feta', 200, 'g'),
                ('Oliwki czarne', 100, 'g'),
                ('Oliwa z oliwek', 3, 'łyżka'),
                ('Sól', 1, 'łyżeczka')
            ],
            'preparation': 'Warzywa pokroić w kostkę. Ser feta pokroić w kostkę. Wszystko wymieszać, dodać oliwki, doprawić solą i polać oliwą.'
        },
        {
            'title': 'Rosół',
            'description': 'Tradycyjny rosół z kurczaka i warzyw',
            'preparation_time': 120,
            'servings': 6,
            'difficulty': 'medium',
            'categories': ['Zupy'],
            'ingredients': [
                ('Kurczak', 1, 'kg'),
                ('Marchew', 3, 'szt'),
                ('Pietruszka', 2, 'szt'),
                ('Seler', 200, 'g'),
                ('Por', 1, 'szt'),
                ('Cebula', 1, 'szt'),
                ('Woda', 3, 'l'),
                ('Makaron', 200, 'g'),
                ('Sól', 2, 'łyżeczka')
            ],
            'preparation': 'Kurczaka umyć, włożyć do zimnej wody. Warzywa obrać, umyć i dodać do garnka. Gotować na małym ogniu przez 2 godziny. Przecedzić. Makaron ugotować osobno. Podawać z makaronem i posiekaną natką pietruszki.'
        },
        {
            'title': 'Pancakes',
            'description': 'Puszyste amerykańskie naleśniki',
            'preparation_time': 30,
            'servings': 4,
            'difficulty': 'easy',
            'categories': ['Śniadania', 'Desery'],
            'ingredients': [
                ('Mąka pszenna', 250, 'g'),
                ('Jajka', 2, 'szt'),
                ('Mleko', 300, 'ml'),
                ('Cukier', 2, 'łyżka'),
                ('Proszek do pieczenia', 2, 'łyżeczka'),
                ('Masło', 50, 'g')
            ],
            'preparation': 'Wszystkie składniki wymieszać na jednolite ciasto. Smażyć na rozgrzanej patelni nakładając małe porcje ciasta. Gdy pojawią się bąbelki na powierzchni, przewrócić. Podawać z syropem klonowym lub owocami.'
        },
        {
            'title': 'Gulasz wieprzowy',
            'description': 'Aromatyczny gulasz z wieprzowiny z warzywami',
            'preparation_time': 90,
            'servings': 6,
            'difficulty': 'medium',
            'categories': ['Dania główne'],
            'ingredients': [
                ('Łopatka wieprzowa', 800, 'g'),
                ('Cebula', 2, 'szt'),
                ('Czosnek', 3, 'szt'),
                ('Papryka', 2, 'szt'),
                ('Marchew', 2, 'szt'),
                ('Pomidory', 4, 'szt'),
                ('Ziemniaki', 600, 'g'),
                ('Sól', 2, 'łyżeczka')
            ],
            'preparation': 'Mięso pokroić w kostkę i obsmażyć. Dodać pokrojone warzywa, doprawić i dusić pod przykryciem około 1 godziny. Na końcu dodać pokrojone ziemniaki i gotować do miękkości.'
        }
    ]
    
    # Tworzenie przepisów
    created_count = 0
    for recipe_data in recipes:
        # Sprawdź czy przepis już istnieje
        exists = Recipe.objects.filter(title=recipe_data['title']).exists()
        if exists:
            print(f"Przepis '{recipe_data['title']}' już istnieje, pomijam")
            continue
            
        # Utwórz nowy przepis
        recipe = Recipe(
            title=recipe_data['title'],
            description=recipe_data['description'],
            preparation_time=recipe_data['preparation_time'],
            servings=recipe_data['servings'],
            difficulty=recipe_data['difficulty'],
            author=admin,
            instructions=recipe_data['preparation'],
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        recipe.save()
        
        # Dodaj kategorie
        for category_name in recipe_data['categories']:
            for category in category_objects:
                if category.name == category_name:
                    recipe.categories.add(category)
        
        # Dodaj składniki
        for ingredient_name, amount, unit_symbol in recipe_data['ingredients']:
            if ingredient_name in ingredient_objects and unit_symbol in unit_objects:
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=ingredient_objects[ingredient_name],
                    amount=amount,
                    unit=unit_objects[unit_symbol]
                )
        
        created_count += 1
        print(f"Utworzono przepis: {recipe.title}")
    
    print(f"Utworzono {created_count} nowych przepisów")
    return True

if __name__ == "__main__":
    create_test_recipes() 