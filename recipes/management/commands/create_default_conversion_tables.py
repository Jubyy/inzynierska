from django.core.management.base import BaseCommand
from recipes.models import ConversionTable, ConversionTableEntry, MeasurementUnit
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Tworzy domyślne tablice konwersji dla składników'

    def handle(self, *args, **kwargs):
        # Pobierz administratora lub utwórz domyślnego, jeśli nie istnieje
        admin_user = None
        if User.objects.filter(is_superuser=True).exists():
            admin_user = User.objects.filter(is_superuser=True).first()
        
        # Pobierz jednostki miary
        try:
            # Jednostki wagowe
            g = MeasurementUnit.objects.get(symbol='g')
            kg = MeasurementUnit.objects.get(symbol='kg')
            
            # Jednostki objętości
            ml = MeasurementUnit.objects.get(symbol='ml')
            l = MeasurementUnit.objects.get(symbol='l')
            
            # Jednostki sztukowe
            szt = MeasurementUnit.objects.get(symbol='szt')
            
            # Jednostki łyżkowe
            tbsp = MeasurementUnit.objects.get(symbol='tbsp')  # łyżka stołowa
            tsp = MeasurementUnit.objects.get(symbol='tsp')    # łyżeczka
            
            # Inne
            szklanka = MeasurementUnit.objects.filter(name__icontains='szklanka').first()
            if not szklanka:
                szklanka = MeasurementUnit.objects.create(
                    name='Szklanka',
                    symbol='szklanka',
                    type='volume',
                    base_ratio=250,
                    is_common=True,
                    description='Standardowa szklanka kuchenna (250ml)'
                )
                self.stdout.write(self.style.SUCCESS(f'Utworzono jednostkę: {szklanka.name}'))
            
        except MeasurementUnit.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'Błąd: Brak wymaganych jednostek miary: {str(e)}'))
            self.stdout.write(self.style.WARNING('Uruchom komendę create_measurement_units przed utworzeniem tablic konwersji.'))
            return

        # Lista kategorii dla których chcemy utworzyć tablice konwersji
        product_categories = [
            # Kategoria, nazwa tablicy, opis tablicy, gęstość, waga sztuki (g)
            ('Mąka', 'Mąka pszenna', 'Standardowe przeliczniki dla mąki pszennej i innych produktów sypkich', 0.6, None),
            ('Cukier', 'Cukier biały', 'Standardowe przeliczniki dla cukru białego i innych produktów sypkich', 0.85, None),
            ('Płyny', 'Mleko', 'Standardowe przeliczniki dla mleka i podobnych płynów', 1.03, None),
            ('Płyny', 'Olej/Oliwa', 'Standardowe przeliczniki dla oleju, oliwy i podobnych tłuszczów', 0.92, None),
            ('Owoce', 'Jabłka', 'Standardowe przeliczniki dla jabłek i podobnych owoców', None, 180),
            ('Owoce', 'Banany', 'Standardowe przeliczniki dla bananów', None, 120),
            ('Warzywa', 'Ziemniaki', 'Standardowe przeliczniki dla ziemniaków', None, 150),
            ('Warzywa', 'Pomidory', 'Standardowe przeliczniki dla pomidorów', None, 125),
            ('Mięso', 'Mięso', 'Standardowe przeliczniki dla różnych rodzajów mięsa', 1.05, None),
            ('Nabiał', 'Ser żółty', 'Standardowe przeliczniki dla sera żółtego', 1.03, None),
            ('Nabiał', 'Ser biały', 'Standardowe przeliczniki dla sera białego i twarogu', 1.02, None),
            ('Przyprawy', 'Przyprawy sypkie', 'Standardowe przeliczniki dla przypraw sypkich', 0.5, None),
        ]
        
        # Utwórz tablice konwersji dla wszystkich kategorii
        for product_type, name, description, density, piece_weight in product_categories:
            self._create_conversion_table(
                product_type=product_type,
                name=name,
                description=description,
                density=density,
                piece_weight=piece_weight,
                admin_user=admin_user,
                g=g, kg=kg, ml=ml, l=l, szt=szt, tbsp=tbsp, tsp=tsp, szklanka=szklanka
            )
        
        self.stdout.write(self.style.SUCCESS('Domyślne tablice konwersji zostały utworzone!'))

    def _create_conversion_table(self, product_type, name, description, density, piece_weight, admin_user, 
                                g, kg, ml, l, szt, tbsp, tsp, szklanka):
        """Tworzy tablicę konwersji z odpowiednimi wpisami"""
        
        table, created = ConversionTable.objects.get_or_create(
            name=name,
            defaults={
                'product_type': product_type,
                'description': description,
                'is_approved': True,
                'created_by': admin_user
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Utworzono tablicę konwersji: {table.name}'))
            
            entries = []
            
            # 1. Podstawowe konwersje wagowe (zawsze)
            entries.extend([
                (g, kg, 0.001, True, 'Podstawowa konwersja'),
                (kg, g, 1000, True, 'Podstawowa konwersja'),
            ])
            
            # 2. Łyżki i łyżeczki dla produktów sypkich i płynów
            if product_type in ['Mąka', 'Cukier', 'Przyprawy']:
                # Dla produktów sypkich - konwersje łyżek na gramy
                tbsp_g = 15 if product_type == 'Mąka' else 20 if product_type == 'Cukier' else 5
                tsp_g = 5 if product_type == 'Mąka' else 7 if product_type == 'Cukier' else 1
                
                entries.extend([
                    (g, tbsp, 1/tbsp_g, True, f'Jedna łyżka to ok. {tbsp_g}g'),
                    (tbsp, g, tbsp_g, True, f'Jedna łyżka to ok. {tbsp_g}g'),
                    (g, tsp, 1/tsp_g, True, f'Jedna łyżeczka to ok. {tsp_g}g'),
                    (tsp, g, tsp_g, True, f'Jedna łyżeczka to ok. {tsp_g}g'),
                ])
                
                # Dla produktów sypkich - konwersje szklanki na gramy
                cup_g = 130 if product_type == 'Mąka' else 200 if product_type == 'Cukier' else 120
                
                entries.extend([
                    (g, szklanka, 1/cup_g, True, f'Jedna szklanka to ok. {cup_g}g'),
                    (szklanka, g, cup_g, True, f'Jedna szklanka to ok. {cup_g}g'),
                ])
                
            elif product_type == 'Płyny':
                # Dla płynów - konwersje łyżek na ml
                entries.extend([
                    (ml, tbsp, 1/15, True, 'Jedna łyżka to ok. 15ml'),
                    (tbsp, ml, 15, True, 'Jedna łyżka to ok. 15ml'),
                    (ml, tsp, 1/5, True, 'Jedna łyżeczka to ok. 5ml'),
                    (tsp, ml, 5, True, 'Jedna łyżeczka to ok. 5ml'),
                    (ml, szklanka, 1/250, True, 'Jedna szklanka to 250ml'),
                    (szklanka, ml, 250, True, 'Jedna szklanka to 250ml'),
                    (ml, l, 0.001, True, 'Podstawowa konwersja'),
                    (l, ml, 1000, True, 'Podstawowa konwersja'),
                ])
            
            # 3. Konwersje wagowo-objętościowe (jeśli jest gęstość)
            if density:
                entries.extend([
                    (ml, g, density, True, f'Gęstość {name}: {density} g/ml'),
                    (g, ml, 1/density, True, f'Gęstość {name}: {density} g/ml'),
                ])
            
            # 4. Konwersje na sztuki (jeśli jest waga sztuki)
            if piece_weight:
                entries.extend([
                    (szt, g, piece_weight, False, f'{name}: 1 sztuka waży ok. {piece_weight}g'),
                    (g, szt, 1/piece_weight, False, f'{name}: 1 sztuka waży ok. {piece_weight}g'),
                ])
                
                # Dodatkowe konwersje dla owoców i warzyw
                if product_type in ['Owoce', 'Warzywa']:
                    # Przybliżona ilość pokrojonych kawałków w szklance
                    cup_pieces = 1.5
                    entries.extend([
                        (szt, szklanka, cup_pieces, False, f'Z jednej sztuki {name} otrzymuje się ok. {cup_pieces} szklanki pokrojonych kawałków'),
                        (szklanka, szt, 1/cup_pieces, False, f'Z jednej sztuki {name} otrzymuje się ok. {cup_pieces} szklanki pokrojonych kawałków'),
                    ])
            
            # Zapisz wszystkie wpisy
            for from_unit, to_unit, ratio, is_exact, notes in entries:
                ConversionTableEntry.objects.create(
                    table=table,
                    from_unit=from_unit,
                    to_unit=to_unit,
                    ratio=ratio,
                    is_exact=is_exact,
                    notes=notes
                )
        else:
            self.stdout.write(self.style.WARNING(f'Tablica konwersji już istnieje: {table.name}'))
        
        return table 