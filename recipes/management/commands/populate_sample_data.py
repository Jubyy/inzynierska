from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from recipes.models import (
    IngredientCategory, Ingredient, MeasurementUnit, UnitConversion,
    RecipeCategory, Recipe, RecipeIngredient
)
from fridge.models import FridgeItem
import random
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generuje przykładowe dane dla aplikacji'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generowanie przykładowych danych...')
        
        # Utwórz testowego użytkownika, jeśli nie istnieje
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_active': True,
            }
        )
        
        if created:
            user.set_password('testpassword')
            user.save()
            self.stdout.write(self.style.SUCCESS('Utworzono użytkownika testowego: testuser/testpassword'))
        
        # Kategorie składników
        categories = [
            {'name': 'Mięso', 'is_vegetarian': False, 'is_vegan': False},
            {'name': 'Nabiał', 'is_vegetarian': True, 'is_vegan': False},
            {'name': 'Warzywa', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Owoce', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Zboża', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Przyprawy', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Oleje i tłuszcze', 'is_vegetarian': True, 'is_vegan': True},
        ]
        
        category_objects = {}
        for cat_data in categories:
            category, created = IngredientCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'is_vegetarian': cat_data['is_vegetarian'],
                    'is_vegan': cat_data['is_vegan']
                }
            )
            category_objects[cat_data['name']] = category
        
        self.stdout.write(self.style.SUCCESS('Utworzono kategorie składników'))
        
        # Jednostki miary
        units = [
            {'name': 'Gram', 'symbol': 'g', 'is_base': True},
            {'name': 'Kilogram', 'symbol': 'kg', 'is_base': False},
            {'name': 'Mililitr', 'symbol': 'ml', 'is_base': True},
            {'name': 'Litr', 'symbol': 'l', 'is_base': False},
            {'name': 'Łyżeczka', 'symbol': 'łyż.', 'is_base': False},
            {'name': 'Łyżka', 'symbol': 'łyżka', 'is_base': False},
            {'name': 'Szklanka', 'symbol': 'szklanka', 'is_base': False},
            {'name': 'Sztuka', 'symbol': 'szt.', 'is_base': True},
        ]
        
        unit_objects = {}
        for unit_data in units:
            unit, created = MeasurementUnit.objects.get_or_create(
                name=unit_data['name'],
                defaults={
                    'symbol': unit_data['symbol'],
                    'is_base': unit_data['is_base']
                }
            )
            unit_objects[unit_data['name']] = unit
        
        self.stdout.write(self.style.SUCCESS('Utworzono jednostki miary'))
        
        # Konwersje jednostek
        conversions = [
            {'from_unit': 'Kilogram', 'to_unit': 'Gram', 'ratio': 1000},
            {'from_unit': 'Gram', 'to_unit': 'Kilogram', 'ratio': 0.001},
            {'from_unit': 'Litr', 'to_unit': 'Mililitr', 'ratio': 1000},
            {'from_unit': 'Mililitr', 'to_unit': 'Litr', 'ratio': 0.001},
            {'from_unit': 'Łyżka', 'to_unit': 'Mililitr', 'ratio': 15},
            {'from_unit': 'Łyżeczka', 'to_unit': 'Mililitr', 'ratio': 5},
            {'from_unit': 'Szklanka', 'to_unit': 'Mililitr', 'ratio': 250},
        ]
        
        for conv_data in conversions:
            UnitConversion.objects.get_or_create(
                from_unit=unit_objects[conv_data['from_unit']],
                to_unit=unit_objects[conv_data['to_unit']],
                defaults={'ratio': conv_data['ratio']}
            )
        
        self.stdout.write(self.style.SUCCESS('Utworzono konwersje jednostek'))
        
        # Składniki
        ingredients = [
            {'name': 'Kurczak', 'category': 'Mięso', 'description': 'Mięso drobiowe'},
            {'name': 'Wołowina', 'category': 'Mięso', 'description': 'Mięso wołowe'},
            {'name': 'Mleko', 'category': 'Nabiał', 'description': 'Mleko krowie'},
            {'name': 'Jajka', 'category': 'Nabiał', 'description': 'Jajka kurze'},
            {'name': 'Ser żółty', 'category': 'Nabiał', 'description': 'Ser dojrzewający'},
            {'name': 'Pomidory', 'category': 'Warzywa', 'description': 'Świeże pomidory'},
            {'name': 'Ogórki', 'category': 'Warzywa', 'description': 'Świeże ogórki'},
            {'name': 'Cebula', 'category': 'Warzywa', 'description': 'Cebula żółta'},
            {'name': 'Czosnek', 'category': 'Warzywa', 'description': 'Czosnek świeży'},
            {'name': 'Marchew', 'category': 'Warzywa', 'description': 'Marchew świeża'},
            {'name': 'Jabłka', 'category': 'Owoce', 'description': 'Jabłka słodkie'},
            {'name': 'Banany', 'category': 'Owoce', 'description': 'Banany dojrzałe'},
            {'name': 'Mąka pszenna', 'category': 'Zboża', 'description': 'Mąka typu 500'},
            {'name': 'Ryż', 'category': 'Zboża', 'description': 'Ryż biały'},
            {'name': 'Sól', 'category': 'Przyprawy', 'description': 'Sól kuchenna'},
            {'name': 'Pieprz', 'category': 'Przyprawy', 'description': 'Pieprz czarny mielony'},
            {'name': 'Oliwa z oliwek', 'category': 'Oleje i tłuszcze', 'description': 'Oliwa extra virgin'},
            {'name': 'Masło', 'category': 'Oleje i tłuszcze', 'description': 'Masło 82%'},
        ]
        
        ingredient_objects = {}
        for ing_data in ingredients:
            ingredient, created = Ingredient.objects.get_or_create(
                name=ing_data['name'],
                defaults={
                    'category': category_objects[ing_data['category']],
                    'description': ing_data['description']
                }
            )
            ingredient_objects[ing_data['name']] = ingredient
        
        self.stdout.write(self.style.SUCCESS('Utworzono składniki'))
        
        # Kategorie przepisów
        recipe_categories = [
            {'name': 'Śniadania', 'description': 'Przepisy na śniadania'},
            {'name': 'Obiady', 'description': 'Przepisy na obiady'},
            {'name': 'Kolacje', 'description': 'Przepisy na kolacje'},
            {'name': 'Desery', 'description': 'Przepisy na desery'},
            {'name': 'Przekąski', 'description': 'Przepisy na przekąski'},
        ]
        
        recipe_category_objects = {}
        for cat_data in recipe_categories:
            category, created = RecipeCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            recipe_category_objects[cat_data['name']] = category
        
        self.stdout.write(self.style.SUCCESS('Utworzono kategorie przepisów'))
        
        # Przepisy
        recipes = [
            {
                'title': 'Jajecznica z pomidorami',
                'description': 'Prosta jajecznica z dodatkiem świeżych pomidorów i cebuli.',
                'instructions': '''
                1. Pokrój cebulę w kostkę i podsmaż na maśle.
                2. Dodaj pokrojone pomidory i smaż przez 2-3 minuty.
                3. Wbij jajka i mieszaj do ścięcia.
                4. Dopraw solą i pieprzem.
                5. Podawaj z pieczywem.
                ''',
                'servings': 2,
                'preparation_time': 15,
                'categories': ['Śniadania'],
                'ingredients': [
                    {'ingredient': 'Jajka', 'amount': 4, 'unit': 'Sztuka'},
                    {'ingredient': 'Pomidory', 'amount': 2, 'unit': 'Sztuka'},
                    {'ingredient': 'Cebula', 'amount': 1, 'unit': 'Sztuka'},
                    {'ingredient': 'Masło', 'amount': 20, 'unit': 'Gram'},
                    {'ingredient': 'Sól', 'amount': 1, 'unit': 'Łyżeczka'},
                    {'ingredient': 'Pieprz', 'amount': 0.5, 'unit': 'Łyżeczka'},
                ]
            },
            {
                'title': 'Spaghetti Bolognese',
                'description': 'Klasyczne spaghetti z sosem mięsnym.',
                'instructions': '''
                1. W garnku rozgrzej oliwę i podsmaż posiekaną cebulę i czosnek.
                2. Dodaj mielone mięso i smaż do zrumienienia.
                3. Dodaj pomidory, sól, pieprz i gotuj na małym ogniu przez 20 minut.
                4. Ugotuj makaron zgodnie z instrukcją na opakowaniu.
                5. Podawaj makaron z sosem.
                ''',
                'servings': 4,
                'preparation_time': 35,
                'categories': ['Obiady'],
                'ingredients': [
                    {'ingredient': 'Wołowina', 'amount': 500, 'unit': 'Gram'},
                    {'ingredient': 'Pomidory', 'amount': 4, 'unit': 'Sztuka'},
                    {'ingredient': 'Cebula', 'amount': 1, 'unit': 'Sztuka'},
                    {'ingredient': 'Czosnek', 'amount': 2, 'unit': 'Sztuka'},
                    {'ingredient': 'Oliwa z oliwek', 'amount': 2, 'unit': 'Łyżka'},
                    {'ingredient': 'Sól', 'amount': 1, 'unit': 'Łyżeczka'},
                    {'ingredient': 'Pieprz', 'amount': 0.5, 'unit': 'Łyżeczka'},
                ]
            },
            {
                'title': 'Sałatka z kurczakiem',
                'description': 'Lekka sałatka z grillowanym kurczakiem i warzywami.',
                'instructions': '''
                1. Pokrój kurczaka w kostkę, dopraw solą i pieprzem, usmaż na oliwie.
                2. Umyj i pokrój warzywa.
                3. Wymieszaj wszystkie składniki w misce.
                4. Skrop oliwą, dopraw solą i pieprzem.
                ''',
                'servings': 2,
                'preparation_time': 20,
                'categories': ['Kolacje', 'Obiady'],
                'ingredients': [
                    {'ingredient': 'Kurczak', 'amount': 300, 'unit': 'Gram'},
                    {'ingredient': 'Pomidory', 'amount': 2, 'unit': 'Sztuka'},
                    {'ingredient': 'Ogórki', 'amount': 1, 'unit': 'Sztuka'},
                    {'ingredient': 'Cebula', 'amount': 0.5, 'unit': 'Sztuka'},
                    {'ingredient': 'Oliwa z oliwek', 'amount': 2, 'unit': 'Łyżka'},
                    {'ingredient': 'Sól', 'amount': 0.5, 'unit': 'Łyżeczka'},
                    {'ingredient': 'Pieprz', 'amount': 0.5, 'unit': 'Łyżeczka'},
                ]
            }
        ]
        
        for recipe_data in recipes:
            recipe, created = Recipe.objects.get_or_create(
                title=recipe_data['title'],
                defaults={
                    'description': recipe_data['description'],
                    'instructions': recipe_data['instructions'],
                    'servings': recipe_data['servings'],
                    'preparation_time': recipe_data['preparation_time'],
                    'author': user,
                }
            )
            
            if created:
                # Dodaj kategorie przepisu
                for category_name in recipe_data['categories']:
                    recipe.categories.add(recipe_category_objects[category_name])
                
                # Dodaj składniki przepisu
                for ing_data in recipe_data['ingredients']:
                    RecipeIngredient.objects.get_or_create(
                        recipe=recipe,
                        ingredient=ingredient_objects[ing_data['ingredient']],
                        defaults={
                            'amount': ing_data['amount'],
                            'unit': unit_objects[ing_data['unit']]
                        }
                    )
        
        self.stdout.write(self.style.SUCCESS('Utworzono przepisy'))
        
        # Produkty w lodówce
        fridge_items = [
            {'ingredient': 'Jajka', 'amount': 10, 'unit': 'Sztuka', 'days_to_expiry': 14},
            {'ingredient': 'Mleko', 'amount': 1, 'unit': 'Litr', 'days_to_expiry': 7},
            {'ingredient': 'Masło', 'amount': 200, 'unit': 'Gram', 'days_to_expiry': 30},
            {'ingredient': 'Ser żółty', 'amount': 300, 'unit': 'Gram', 'days_to_expiry': 14},
            {'ingredient': 'Kurczak', 'amount': 500, 'unit': 'Gram', 'days_to_expiry': 3},
            {'ingredient': 'Pomidory', 'amount': 5, 'unit': 'Sztuka', 'days_to_expiry': 7},
            {'ingredient': 'Ogórki', 'amount': 3, 'unit': 'Sztuka', 'days_to_expiry': 10},
            {'ingredient': 'Cebula', 'amount': 4, 'unit': 'Sztuka', 'days_to_expiry': 30},
            {'ingredient': 'Jabłka', 'amount': 6, 'unit': 'Sztuka', 'days_to_expiry': 14},
            {'ingredient': 'Banany', 'amount': 4, 'unit': 'Sztuka', 'days_to_expiry': 5},
            {'ingredient': 'Mąka pszenna', 'amount': 1, 'unit': 'Kilogram', 'days_to_expiry': 180},
            {'ingredient': 'Ryż', 'amount': 500, 'unit': 'Gram', 'days_to_expiry': 365},
            {'ingredient': 'Sól', 'amount': 500, 'unit': 'Gram', 'days_to_expiry': 1825},
            {'ingredient': 'Pieprz', 'amount': 100, 'unit': 'Gram', 'days_to_expiry': 730},
            {'ingredient': 'Oliwa z oliwek', 'amount': 500, 'unit': 'Mililitr', 'days_to_expiry': 365},
        ]
        
        for item_data in fridge_items:
            today = timezone.now().date()
            expiry_date = today + timedelta(days=item_data['days_to_expiry'])
            
            FridgeItem.objects.get_or_create(
                user=user,
                ingredient=ingredient_objects[item_data['ingredient']],
                unit=unit_objects[item_data['unit']],
                defaults={
                    'amount': item_data['amount'],
                    'expiry_date': expiry_date,
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Utworzono produkty w lodówce'))
        
        self.stdout.write(self.style.SUCCESS('Generowanie przykładowych danych zakończone!')) 