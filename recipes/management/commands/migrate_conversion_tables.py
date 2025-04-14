from django.core.management.base import BaseCommand
from recipes.models import ConversionTable, IngredientCategory
from django.db import transaction
from django.db.models import F

class Command(BaseCommand):
    help = 'Migruje istniejące tablice konwersji do nowej struktury z powiązaniami do kategorii'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Rozpoczynam migrację tablic konwersji...')
        
        # Pobierz wszystkie kategorie
        categories = {}
        for category in IngredientCategory.objects.all():
            categories[category.name.lower()] = category
        
        # Kategorie na potrzeby migracji
        migration_map = {
            'mąka': 'Mąka i produkty sypkie',
            'cukier': 'Mąka i produkty sypkie',
            'płyny': 'Nabiał',  # Domyślnie płyny przypisujemy do nabiału
            'owoce': 'Owoce',
            'warzywa': 'Warzywa',
            'mięso': 'Mięso',
            'wędliny': 'Mięso',
            'nabiał': 'Nabiał',
            'przyprawy': 'Przyprawy',
        }
        
        # Mapowanie flagi is_for_liquids
        liquids = ['płyny', 'mleko', 'woda', 'olej', 'sok']
        
        # Migruj każdą tablicę konwersji
        tables_updated = 0
        for table in ConversionTable.objects.all():
            # Pobierz typ produktu
            product_type = table.product_type.lower() if hasattr(table, 'product_type') else ''
            
            if not product_type:
                self.stdout.write(self.style.WARNING(f'Tablica {table.name} nie ma określonego typu produktu. Pomijam.'))
                continue
                
            # Znajdź odpowiednią kategorię
            target_category_name = None
            
            # Szukaj bezpośredniego dopasowania
            for key, cat_name in migration_map.items():
                if key in product_type:
                    target_category_name = cat_name
                    break
            
            # Jeśli nie znaleziono, przypisz do "Inne"
            if not target_category_name:
                self.stdout.write(self.style.WARNING(f'Nie znaleziono odpowiedniej kategorii dla {product_type}. Przypisuję do "Inne".'))
                target_category_name = 'Inne'
            
            # Pobierz lub utwórz kategorię
            if target_category_name.lower() in categories:
                target_category = categories[target_category_name.lower()]
            else:
                target_category, created = IngredientCategory.objects.get_or_create(name=target_category_name)
                categories[target_category_name.lower()] = target_category
                if created:
                    self.stdout.write(f'Utworzono nową kategorię: {target_category_name}')
            
            # Określ czy produkt jest płynny
            is_liquid = any(liquid in product_type.lower() for liquid in liquids)
            
            # Aktualizuj tablicę konwersji
            try:
                table.category = target_category
                table.is_for_liquids = is_liquid
                table.save(update_fields=['category', 'is_for_liquids'])
                tables_updated += 1
                self.stdout.write(f'Zaktualizowano tablicę: {table.name} -> kategoria: {target_category.name}, płyn: {is_liquid}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Błąd podczas aktualizacji tablicy {table.name}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono migrację tablic konwersji. Zaktualizowano {tables_updated} tablic.')) 