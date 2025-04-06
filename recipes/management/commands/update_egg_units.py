from django.core.management.base import BaseCommand
from recipes.models import Ingredient, MeasurementUnit

class Command(BaseCommand):
    help = 'Naprawia jednostki dla jajek i innych produktów sprzedawanych na sztuki'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Rozpoczynam naprawę jednostek dla jajek...'))
        
        # Upewnij się, że mamy jednostkę typu piece (sztuka)
        sztuka, created = MeasurementUnit.objects.get_or_create(
            symbol='szt',
            defaults={
                'name': 'Sztuka',
                'type': 'piece',
                'base_ratio': 1.0,
                'is_common': True,
                'description': 'Jednostka dla produktów sprzedawanych na sztuki'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Utworzono jednostkę "Sztuka"'))
        else:
            # Upewnij się że jednostka ma właściwy typ
            if sztuka.type != 'piece':
                sztuka.type = 'piece'
                sztuka.save()
                self.stdout.write(self.style.SUCCESS('Zaktualizowano typ jednostki "Sztuka" na "piece"'))
        
        # Znajdź jajka i inne produkty sprzedawane na sztuki
        pieces_products = [
            'Jajka', 'Jajko', 'Jajo', 'Jaja', 
            'Bułka', 'Bułki', 'Chleb',
            'Cebula', 'Cebule', 'Czosnek',
            'Papryka', 'Papryki', 'Pomidor', 'Pomidory',
            'Ogórek', 'Ogórki', 'Cytryna', 'Cytryny',
            'Banan', 'Banany', 'Jabłko', 'Jabłka'
        ]
        
        # Zaktualizuj każdy składnik
        updated = 0
        for name in pieces_products:
            ingredients = Ingredient.objects.filter(name__icontains=name)
            for ingredient in ingredients:
                # Sprawdź czy to jajka - wtedy tylko piece_only
                if 'jaj' in ingredient.name.lower():
                    ingredient.unit_type = 'piece_only'
                    ingredient.default_unit = sztuka
                    ingredient.save()
                    
                    # Dodaj jednostkę do kompatybilnych
                    ingredient.compatible_units.add(sztuka)
                    
                    self.stdout.write(self.style.SUCCESS(f'Zaktualizowano "{ingredient.name}" - tylko sztuki'))
                # Dla warzyw i owoców ustaw piece_weight
                elif ingredient.unit_type != 'piece_only' and ingredient.unit_type != 'weight_piece':
                    ingredient.unit_type = 'weight_piece'
                    ingredient.save()
                    
                    # Dodaj jednostkę do kompatybilnych
                    ingredient.compatible_units.add(sztuka)
                    
                    self.stdout.write(self.style.SUCCESS(f'Zaktualizowano "{ingredient.name}" - waga i sztuki'))
                
                updated += 1
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono aktualizację {updated} składników'))
        
        # Upewnij się, że jajka są ustawione prawidłowo
        jajka = Ingredient.objects.filter(name__icontains='jajk')
        if jajka.exists():
            for j in jajka:
                j.unit_type = 'piece_only'
                j.default_unit = sztuka
                j.save()
                
                # Upewnij się, że sztuki są w kompatybilnych jednostkach
                j.compatible_units.add(sztuka)
                
                self.stdout.write(self.style.SUCCESS(f'Zaktualizowano "{j.name}" - ustawiono domyślną jednostkę na "Sztuka"')) 