from django.core.management.base import BaseCommand
from recipes.models import Ingredient, MeasurementUnit

class Command(BaseCommand):
    help = 'Poprawia konfigurację jednostek dla wszystkich składników'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Rozpoczynam aktualizację jednostek dla wszystkich składników...'))
        
        # Upewnij się, że mamy wszystkie podstawowe jednostki
        units = {
            'weight': {
                'g': self.get_or_create_unit('Gram', 'g', 'weight', 1.0),
                'kg': self.get_or_create_unit('Kilogram', 'kg', 'weight', 1000.0),
            },
            'volume': {
                'ml': self.get_or_create_unit('Mililitr', 'ml', 'volume', 1.0),
                'l': self.get_or_create_unit('Litr', 'l', 'volume', 1000.0),
            },
            'piece': {
                'szt': self.get_or_create_unit('Sztuka', 'szt', 'piece', 1.0),
            },
            'spoon': {
                'łyżka': self.get_or_create_unit('Łyżka', 'łyżka', 'spoon', 15.0),
                'łyżeczka': self.get_or_create_unit('Łyżeczka', 'łyżeczka', 'spoon', 5.0),
            }
        }
        
        # Lista składników z domyślnymi jednostkami na podstawie unit_type
        unit_type_defaults = {
            'weight_only': units['weight']['g'],
            'volume_only': units['volume']['ml'],
            'piece_only': units['piece']['szt'],
            'weight_volume': units['weight']['g'],
            'weight_piece': units['weight']['g'],
            'weight_spoon': units['weight']['g'],
            'volume_spoon': units['volume']['ml'],
            'all': units['weight']['g'],
        }
        
        # Zaktualizuj każdy składnik
        updated = 0
        for ingredient in Ingredient.objects.all():
            try:
                # Ustaw domyślną jednostkę, jeśli brak
                if not ingredient.default_unit:
                    default_unit = unit_type_defaults.get(ingredient.unit_type)
                    if default_unit:
                        ingredient.default_unit = default_unit
                        ingredient.save()
                        self.stdout.write(f'Ustawiono domyślną jednostkę dla "{ingredient.name}"')
                
                # Dodaj wszystkie kompatybilne jednostki na podstawie unit_type
                allowed_units = ingredient.get_allowed_units()
                for unit in allowed_units:
                    if unit not in ingredient.compatible_units.all():
                        ingredient.compatible_units.add(unit)
                        self.stdout.write(f'Dodano jednostkę {unit.name} do "{ingredient.name}"')
                
                # Napraw specyficzne składniki
                self.fix_special_ingredient(ingredient, units)
                
                updated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Błąd podczas aktualizacji "{ingredient.name}": {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono aktualizację {updated} składników'))

    def get_or_create_unit(self, name, symbol, type, base_ratio):
        """Pobiera lub tworzy jednostkę miary"""
        unit, created = MeasurementUnit.objects.get_or_create(
            symbol=symbol,
            defaults={
                'name': name,
                'type': type,
                'base_ratio': base_ratio,
                'is_common': True,
            }
        )
        
        if not created:
            # Upewnij się, że jednostka ma właściwe ustawienia
            unit.name = name
            unit.type = type
            unit.base_ratio = base_ratio
            unit.is_common = True
            unit.save()
            
        return unit
    
    def fix_special_ingredient(self, ingredient, units):
        """Naprawia specyficzne składniki"""
        name_lower = ingredient.name.lower()
        
        # Warzywa i owoce sprzedawane na sztuki
        vegetables_fruits = ['cebula', 'czosnek', 'papryka', 'pomidor', 'ogórek', 'cytryna', 
                           'pomarańcza', 'jabłko', 'banan', 'ziemniak', 'gruszka']
        
        # Jajka - tylko sztuki
        if 'jaj' in name_lower:
            ingredient.unit_type = 'piece_only'
            ingredient.default_unit = units['piece']['szt']
            ingredient.compatible_units.add(units['piece']['szt'])
            ingredient.save()
            self.stdout.write(f'Naprawiono składnik "{ingredient.name}" - tylko sztuki')
        
        # Warzywa i owoce - waga i sztuki
        elif any(veg in name_lower for veg in vegetables_fruits):
            ingredient.unit_type = 'weight_piece'
            if not ingredient.default_unit:
                ingredient.default_unit = units['weight']['g']
            ingredient.compatible_units.add(units['piece']['szt'])
            ingredient.compatible_units.add(units['weight']['g'])
            ingredient.compatible_units.add(units['weight']['kg'])
            ingredient.save()
            self.stdout.write(f'Naprawiono składnik "{ingredient.name}" - waga i sztuki')
        
        # Płyny - objętość i łyżki
        elif any(liquid in name_lower for liquid in ['olej', 'oliwa', 'mleko', 'śmietana', 'jogurt', 'miód']):
            ingredient.unit_type = 'volume_spoon'
            if not ingredient.default_unit:
                ingredient.default_unit = units['volume']['ml']
            ingredient.compatible_units.add(units['volume']['ml'])
            ingredient.compatible_units.add(units['volume']['l'])
            ingredient.compatible_units.add(units['spoon']['łyżka'])
            ingredient.compatible_units.add(units['spoon']['łyżeczka'])
            ingredient.save()
            self.stdout.write(f'Naprawiono składnik "{ingredient.name}" - objętość i łyżki') 