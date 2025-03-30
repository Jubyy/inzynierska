from django.db import migrations

def setup_units_and_conversions(apps, schema_editor):
    MeasurementUnit = apps.get_model('recipes', 'MeasurementUnit')
    UnitConversion = apps.get_model('recipes', 'UnitConversion')
    Ingredient = apps.get_model('recipes', 'Ingredient')
    IngredientCategory = apps.get_model('recipes', 'IngredientCategory')
    
    # Tworzenie podstawowych jednostek
    units = {
        # Jednostki wagowe
        'g': MeasurementUnit.objects.create(name='Gram', symbol='g', is_base=True),
        'kg': MeasurementUnit.objects.create(name='Kilogram', symbol='kg'),
        'dkg': MeasurementUnit.objects.create(name='Dekagram', symbol='dkg'),
        
        # Jednostki objętości
        'ml': MeasurementUnit.objects.create(name='Mililitr', symbol='ml', is_base=True),
        'l': MeasurementUnit.objects.create(name='Litr', symbol='l'),
        
        # Jednostki sztukowe
        'szt': MeasurementUnit.objects.create(name='Sztuka', symbol='szt', is_base=True),
        
        # Jednostki kuchenne
        'łyżka': MeasurementUnit.objects.create(name='Łyżka', symbol='łyżka'),
        'łyżeczka': MeasurementUnit.objects.create(name='Łyżeczka', symbol='łyżeczka'),
        'szklanka': MeasurementUnit.objects.create(name='Szklanka', symbol='szklanka'),
        'garść': MeasurementUnit.objects.create(name='Garść', symbol='garść'),
    }
    
    # Konwersje jednostek
    conversions = [
        # Konwersje wagowe
        (units['kg'], units['g'], 1000),
        (units['dkg'], units['g'], 10),
        
        # Konwersje objętości
        (units['l'], units['ml'], 1000),
        
        # Konwersje kuchenne dla płynów
        (units['szklanka'], units['ml'], 250),
        (units['łyżka'], units['ml'], 15),
        (units['łyżeczka'], units['ml'], 5),
        
        # Konwersje kuchenne dla sypkich
        (units['szklanka'], units['g'], 200),  # Średnia waga sypkich produktów
        (units['łyżka'], units['g'], 15),      # Średnia waga sypkich produktów
        (units['łyżeczka'], units['g'], 5),    # Średnia waga sypkich produktów
    ]
    
    # Dodawanie konwersji
    for from_unit, to_unit, ratio in conversions:
        UnitConversion.objects.create(
            from_unit=from_unit,
            to_unit=to_unit,
            ratio=ratio
        )
        # Dodaj też konwersję w przeciwnym kierunku
        UnitConversion.objects.create(
            from_unit=to_unit,
            to_unit=from_unit,
            ratio=1/ratio
        )
    
    # Konfiguracja kompatybilnych jednostek dla kategorii
    category_units = {
        'Płyny': [units['ml'], units['l'], units['szklanka'], units['łyżka'], units['łyżeczka']],
        'Produkty sypkie': [units['g'], units['kg'], units['dkg'], units['szklanka'], units['łyżka'], units['łyżeczka']],
        'Owoce i warzywa': [units['g'], units['kg'], units['dkg'], units['szt'], units['garść']],
        'Przyprawy': [units['g'], units['łyżka'], units['łyżeczka']],
        'Nabiał': [units['g'], units['ml'], units['l'], units['szklanka'], units['łyżka']],
        'Mięso': [units['g'], units['kg'], units['dkg']],
    }
    
    # Aktualizacja składników
    for category_name, compatible_units in category_units.items():
        try:
            category = IngredientCategory.objects.get(name=category_name)
            ingredients = Ingredient.objects.filter(category=category)
            
            for ingredient in ingredients:
                # Ustaw domyślną jednostkę
                if category_name in ['Płyny']:
                    ingredient.default_unit = units['ml']
                elif category_name in ['Owoce i warzywa']:
                    ingredient.default_unit = units['szt']
                else:
                    ingredient.default_unit = units['g']
                
                ingredient.save()
                
                # Dodaj kompatybilne jednostki
                ingredient.compatible_units.set(compatible_units)
        except IngredientCategory.DoesNotExist:
            continue

class Migration(migrations.Migration):
    dependencies = [
        ('recipes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(setup_units_and_conversions),
    ] 