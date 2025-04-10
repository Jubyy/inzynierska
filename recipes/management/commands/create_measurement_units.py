from django.core.management.base import BaseCommand
from recipes.models import MeasurementUnit

class Command(BaseCommand):
    help = 'Tworzy podstawowe jednostki miary używane w systemie'

    def handle(self, *args, **kwargs):
        # Jednostki wagowe
        self._create_unit('Gram', 'g', 'weight', 1.0, True, 'Podstawowa jednostka wagi')
        self._create_unit('Kilogram', 'kg', 'weight', 1000.0, True, 'Kilogram = 1000 gramów')
        self._create_unit('Dekagram', 'dag', 'weight', 10.0, True, 'Dekagram = 10 gramów')
        
        # Jednostki objętości
        self._create_unit('Mililitr', 'ml', 'volume', 1.0, True, 'Podstawowa jednostka objętości')
        self._create_unit('Litr', 'l', 'volume', 1000.0, True, 'Litr = 1000 mililitrów')
        
        # Jednostki sztukowe
        self._create_unit('Sztuka', 'szt', 'piece', 1.0, True, 'Podstawowa jednostka ilości')
        self._create_unit('Opakowanie', 'opak.', 'piece', 1.0, True, 'Opakowanie produktu')
        
        # Jednostki łyżkowe
        self._create_unit('Łyżka stołowa', 'tbsp', 'spoon', 15.0, True, 'Łyżka stołowa ≈ 15ml')
        self._create_unit('Łyżeczka', 'tsp', 'spoon', 5.0, True, 'Łyżeczka ≈ 5ml')
        
        # Inne
        self._create_unit('Szklanka', 'szklanka', 'volume', 250.0, True, 'Standardowa szklanka kuchenna (250ml)')
        self._create_unit('Garść', 'garść', 'special', 1.0, False, 'Przybliżona ilość, jaką można zmieścić w dłoni')
        self._create_unit('Szczypta', 'szczypta', 'special', 0.5, False, 'Bardzo mała ilość (zwykle przypraw)')
        
        # Specjalne jednostki dla typowych składników
        self._create_unit('Główka', 'główka', 'piece', 1.0, False, 'Np. główka czosnku, kapusty')
        self._create_unit('Ząbek', 'ząbek', 'piece', 1.0, False, 'Np. ząbek czosnku')
        
        self.stdout.write(self.style.SUCCESS('Podstawowe jednostki miary zostały utworzone!'))
    
    def _create_unit(self, name, symbol, type, base_ratio, is_common, description):
        """
        Pomocnicza metoda do tworzenia jednostek miary
        """
        obj, created = MeasurementUnit.objects.get_or_create(
            symbol=symbol,
            defaults={
                'name': name,
                'type': type,
                'base_ratio': base_ratio,
                'is_common': is_common,
                'description': description
            }
        )
        
        if created:
            self.stdout.write(f'Utworzono jednostkę: {name} ({symbol})')
        else:
            self.stdout.write(f'Jednostka już istnieje: {name} ({symbol})')
            # Aktualizuj istniejącą jednostkę, jeśli się zmieniła definicja
            if obj.name != name or obj.type != type or obj.base_ratio != base_ratio or obj.is_common != is_common:
                obj.name = name
                obj.type = type
                obj.base_ratio = base_ratio
                obj.is_common = is_common
                obj.description = description
                obj.save()
                self.stdout.write(f'Zaktualizowano jednostkę: {name} ({symbol})')
                
        return obj 