from django.core.management.base import BaseCommand
from recipes.models import MeasurementUnit
from decimal import Decimal

class Command(BaseCommand):
    help = 'Dodaje szczegółowe przeliczniki kuchenne do systemu'

    def handle(self, *args, **kwargs):
        self.stdout.write('Dodaję przeliczniki kuchenne...')
        
        # Lista jednostek do dodania lub zaktualizowania
        kitchen_units = [
            # Jednostki objętości
            {
                'name': 'szklanka',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('250.0'),
                'description': '1 szklanka ≈ 250 ml',
                'is_common': True
            },
            {
                'name': 'filiżanka',
                'symbol': 'filiżanka',
                'type': 'volume',
                'base_ratio': Decimal('150.0'),
                'description': '1 filiżanka ≈ 150 ml',
                'is_common': True
            },
            # Jednostki łyżkowe
            {
                'name': 'łyżka',
                'symbol': 'łyżka',
                'type': 'spoon',
                'base_ratio': Decimal('15.0'),
                'description': '1 łyżka ≈ 15 ml lub 15 g',
                'is_common': True
            },
            {
                'name': 'łyżeczka',
                'symbol': 'łyżeczka',
                'type': 'spoon',
                'base_ratio': Decimal('5.0'),
                'description': '1 łyżeczka ≈ 5 ml lub 5 g',
                'is_common': True
            },
            # Specjalne jednostki z przelicznikami
            {
                'name': 'szczypta',
                'symbol': 'szczypta', 
                'type': 'spoon',
                'base_ratio': Decimal('0.5'),
                'description': '1 szczypta ≈ 0.5 g (pół grama)',
                'is_common': True
            },
            # Specyficzne przeliczniki dla popularnych produktów
            {
                'name': 'szklanka mąki pszennej',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('130.0'),
                'description': '1 szklanka mąki ≈ 130 g',
                'is_common': False
            },
            {
                'name': 'szklanka cukru',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('200.0'), 
                'description': '1 szklanka cukru ≈ 200 g',
                'is_common': False
            },
            {
                'name': 'szklanka ryżu',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('180.0'),
                'description': '1 szklanka ryżu ≈ 180 g',
                'is_common': False
            },
            {
                'name': 'szklanka mleka',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('250.0'),
                'description': '1 szklanka mleka ≈ 250 ml',
                'is_common': False
            },
            {
                'name': 'szklanka masła',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('230.0'),
                'description': '1 szklanka masła ≈ 230 g',
                'is_common': False
            },
            {
                'name': 'szklanka miodu',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('340.0'),
                'description': '1 szklanka miodu ≈ 340 g',
                'is_common': False
            },
            {
                'name': 'szklanka oleju',
                'symbol': 'szklanka',
                'type': 'volume',
                'base_ratio': Decimal('220.0'),
                'description': '1 szklanka oleju ≈ 220 g',
                'is_common': False
            }
        ]
        
        # Dodaj lub zaktualizuj jednostki
        added_count = 0
        updated_count = 0
        
        for unit_data in kitchen_units:
            # Sprawdź czy jednostka już istnieje
            unit, created = MeasurementUnit.objects.update_or_create(
                name=unit_data['name'],
                defaults={
                    'symbol': unit_data['symbol'],
                    'type': unit_data['type'],
                    'base_ratio': unit_data['base_ratio'],
                    'description': unit_data['description'],
                    'is_common': unit_data['is_common']
                }
            )
            
            if created:
                added_count += 1
                self.stdout.write(self.style.SUCCESS(f'Dodano jednostkę: {unit.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Zaktualizowano jednostkę: {unit.name}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'Zakończono dodawanie przeliczników kuchennych. Dodano: {added_count}, zaktualizowano: {updated_count}.'
        )) 