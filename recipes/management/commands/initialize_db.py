from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from recipes.models import (
    IngredientCategory, Ingredient, MeasurementUnit, UnitConversion,
    RecipeCategory, Recipe, RecipeIngredient
)
from recipes.utils import get_common_units, get_common_conversions
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Inicjalizuje bazę danych podstawowymi danymi'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Rozpoczynam inicjalizację bazy danych...'))
        
        # Upewnij się, że istnieje katalog mediów
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'recipes'), exist_ok=True)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'avatars'), exist_ok=True)
        
        # 1. Utwórz administratora, jeśli nie istnieje
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write(self.style.SUCCESS('Utworzono użytkownika administratora (login: admin, hasło: admin)'))
        
        # 2. Utwórz kategorie składników
        ingredient_categories = [
            {'name': 'Mięso', 'is_vegetarian': False, 'is_vegan': False},
            {'name': 'Nabiał', 'is_vegetarian': True, 'is_vegan': False},
            {'name': 'Warzywa', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Owoce', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Zboża', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Przyprawy', 'is_vegetarian': True, 'is_vegan': True},
            {'name': 'Produkty pochodzenia zwierzęcego', 'is_vegetarian': True, 'is_vegan': False},
        ]
        
        for cat_data in ingredient_categories:
            IngredientCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'is_vegetarian': cat_data['is_vegetarian'],
                    'is_vegan': cat_data['is_vegan']
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Utworzono {len(ingredient_categories)} kategorii składników'))
        
        # 3. Utwórz podstawowe jednostki miary
        units_data = get_common_units()
        
        for unit_data in units_data:
            MeasurementUnit.objects.get_or_create(
                symbol=unit_data['symbol'],
                defaults={
                    'name': unit_data['name'],
                    'is_base': unit_data['is_base']
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Utworzono {len(units_data)} jednostek miary'))
        
        # 4. Utwórz konwersje między jednostkami
        conversions_data = get_common_conversions()
        created_count = 0
        
        for conv_data in conversions_data:
            try:
                from_unit = MeasurementUnit.objects.get(symbol=conv_data['from'])
                to_unit = MeasurementUnit.objects.get(symbol=conv_data['to'])
                
                UnitConversion.objects.get_or_create(
                    from_unit=from_unit,
                    to_unit=to_unit,
                    defaults={'ratio': conv_data['ratio']}
                )
                created_count += 1
            except MeasurementUnit.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Nie można utworzyć konwersji: {conv_data["from"]} -> {conv_data["to"]}'))
        
        self.stdout.write(self.style.SUCCESS(f'Utworzono {created_count} konwersji jednostek'))
        
        # 5. Utwórz podstawowe składniki
        ingredients_data = [
            {'name': 'Mąka pszenna', 'category': 'Zboża'},
            {'name': 'Cukier', 'category': 'Przyprawy'},
            {'name': 'Sól', 'category': 'Przyprawy'},
            {'name': 'Mleko', 'category': 'Nabiał'},
            {'name': 'Jajka', 'category': 'Produkty pochodzenia zwierzęcego'},
            {'name': 'Masło', 'category': 'Nabiał'},
            {'name': 'Olej', 'category': 'Przyprawy'},
            {'name': 'Drożdże', 'category': 'Przyprawy'},
            {'name': 'Cebula', 'category': 'Warzywa'},
            {'name': 'Czosnek', 'category': 'Warzywa'},
            {'name': 'Ziemniaki', 'category': 'Warzywa'},
            {'name': 'Marchew', 'category': 'Warzywa'},
            {'name': 'Kurczak', 'category': 'Mięso'},
            {'name': 'Wołowina', 'category': 'Mięso'},
            {'name': 'Ser żółty', 'category': 'Nabiał'},
            {'name': 'Jogurt naturalny', 'category': 'Nabiał'},
            {'name': 'Pomidory', 'category': 'Warzywa'},
            {'name': 'Ogórki', 'category': 'Warzywa'},
            {'name': 'Papryka', 'category': 'Warzywa'},
            {'name': 'Jabłka', 'category': 'Owoce'},
            {'name': 'Banany', 'category': 'Owoce'},
            {'name': 'Cytryna', 'category': 'Owoce'},
            {'name': 'Ryż', 'category': 'Zboża'},
            {'name': 'Makaron', 'category': 'Zboża'},
        ]
        
        created_count = 0
        
        for ing_data in ingredients_data:
            try:
                category = IngredientCategory.objects.get(name=ing_data['category'])
                Ingredient.objects.get_or_create(
                    name=ing_data['name'],
                    defaults={'category': category}
                )
                created_count += 1
            except IngredientCategory.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Nie można utworzyć składnika {ing_data["name"]}: kategoria {ing_data["category"]} nie istnieje'))
        
        self.stdout.write(self.style.SUCCESS(f'Utworzono {created_count} składników'))
        
        # 6. Utwórz kategorie przepisów
        recipe_categories = [
            {'name': 'Śniadanie', 'description': 'Przepisy na pyszne śniadania'},
            {'name': 'Obiad', 'description': 'Przepisy na sycące obiady'},
            {'name': 'Kolacja', 'description': 'Przepisy na lekkie kolacje'},
            {'name': 'Deser', 'description': 'Przepisy na słodkie desery'},
            {'name': 'Przekąska', 'description': 'Przepisy na szybkie przekąski'},
        ]
        
        for cat_data in recipe_categories:
            RecipeCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
        
        self.stdout.write(self.style.SUCCESS(f'Utworzono {len(recipe_categories)} kategorii przepisów'))
        
        self.stdout.write(self.style.SUCCESS('Inicjalizacja bazy danych zakończona pomyślnie!'))
        self.stdout.write(self.style.SUCCESS('Aby zalogować się jako administrator, użyj danych:'))
        self.stdout.write(self.style.SUCCESS('Login: admin'))
        self.stdout.write(self.style.SUCCESS('Hasło: admin')) 