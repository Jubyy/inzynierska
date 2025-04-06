from django.core.management.base import BaseCommand
from recipes.models import Ingredient, IngredientCategory

class Command(BaseCommand):
    help = 'Przypisuje odpowiednie typy jednostek (unit_type) dla istniejących składników'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Rozpoczynam przypisywanie typów jednostek...'))
        
        # Definicja mapowania kategorii składników na typy jednostek
        category_to_unit_type = {
            'Mięso': 'weight_only',
            'Wędliny': 'weight_only',
            'Nabiał': 'weight_volume',
            'Warzywa': 'weight_piece',
            'Owoce': 'weight_piece',
            'Zboża': 'weight_only',
            'Przyprawy': 'weight_spoon',
            'Produkty pochodzenia zwierzęcego': 'piece_only',
            'Pieczywo': 'weight_piece',
            'Napoje': 'volume_only',
            'Oleje i tłuszcze': 'weight_volume',
            'Słodycze': 'weight_only',
            'Bakalie': 'weight_only',
            'Przetwory': 'weight_volume',
            'Sosy i dipy': 'volume_spoon',
            'Makarony i ryż': 'weight_only',
            'Przekąski': 'weight_only',
            'Owoce morza': 'weight_only',
            'Jaja': 'piece_only',
            'Mrożonki': 'weight_only',
        }
        
        # Mapowanie nazw składników na typy jednostek - dla specyficznych przypadków
        special_ingredients = {
            'Jajka': 'piece_only',
            'Jajko': 'piece_only',
            'Masło': 'weight_spoon',
            'Olej': 'volume_spoon',
            'Oliwa': 'volume_spoon',
            'Mleko': 'volume_only',
            'Śmietana': 'volume_spoon',
            'Jogurt': 'volume_only',
            'Mąka': 'weight_spoon',
            'Cukier': 'weight_spoon',
            'Sól': 'weight_spoon',
            'Pieprz': 'weight_spoon',
            'Miód': 'volume_spoon',
            'Ocet': 'volume_spoon',
            'Woda': 'volume_only',
            'Wino': 'volume_only',
            'Piwo': 'volume_only',
            'Drożdże': 'weight_only',
            'Cebula': 'weight_piece',
            'Czosnek': 'weight_piece',
            'Ziemniaki': 'weight_piece',
            'Jabłka': 'weight_piece',
            'Cytryna': 'weight_piece',
            'Pomarańcza': 'weight_piece',
            'Banan': 'piece_only',
            'Papryka': 'weight_piece',
            'Ser żółty': 'weight_only',
            'Ser biały': 'weight_only',
            'Makaron': 'weight_only',
            'Ryż': 'weight_only',
            'Kaszę': 'weight_only',
            'Kasza': 'weight_only',
            'Chleb': 'weight_piece',
            'Bułka': 'piece_only',
            'Pomidor': 'weight_piece',
            'Ogórek': 'weight_piece',
        }
        
        # Przypisz unit_type na podstawie nazwy składnika lub jego kategorii
        updated = 0
        for ingredient in Ingredient.objects.all():
            # Najpierw sprawdź po nazwie
            if ingredient.name in special_ingredients:
                ingredient.unit_type = special_ingredients[ingredient.name]
                ingredient.save()
                updated += 1
                continue
                
            # Następnie sprawdź po kategorii
            if ingredient.category and ingredient.category.name in category_to_unit_type:
                ingredient.unit_type = category_to_unit_type[ingredient.category.name]
                ingredient.save()
                updated += 1
            else:
                # Domyślnie przypisz weight_only
                ingredient.unit_type = 'weight_only'
                ingredient.save()
                updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Zakończono przypisywanie typów jednostek dla {updated} składników!')
        ) 