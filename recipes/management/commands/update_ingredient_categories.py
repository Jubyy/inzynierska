from django.core.management.base import BaseCommand
from recipes.models import IngredientCategory

class Command(BaseCommand):
    help = 'Aktualizuje flagi wegetariańskie i wegańskie dla kategorii składników'

    def handle(self, *args, **options):
        categories = IngredientCategory.objects.all()
        updated_count = 0
        
        for category in categories:
            # Zapisz kategorię, co uruchomi metodę save() z logiką automatycznego ustawiania flag
            old_veg = category.is_vegetarian
            old_vegan = category.is_vegan
            
            # Zapisujemy kategorię, co uruchomi logikę automatycznego ustawiania flag
            category.save()
            
            # Sprawdź, czy wartości zostały zmienione
            if old_veg != category.is_vegetarian or old_vegan != category.is_vegan:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Zaktualizowano kategorię "{category.name}": '
                    f'wegetariańska={category.is_vegetarian}, '
                    f'wegańska={category.is_vegan}'
                ))
        
        self.stdout.write(self.style.SUCCESS(f'Zaktualizowano {updated_count} z {categories.count()} kategorii.')) 