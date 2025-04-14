from django.core.management.base import BaseCommand
from recipes.models import ConversionTable, IngredientCategory, MeasurementUnit, ConversionTableEntry
from django.db import transaction
from decimal import Decimal

class Command(BaseCommand):
    help = 'Tworzy lub aktualizuje tablice konwersji dla głównych kategorii produktów'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Tworzenie tablic konwersji dla kategorii produktów...')
        
        # Pobierz lub utwórz kategorie składników
        categories = {
            'warzywa': self.get_or_create_category("Warzywa"),
            'owoce': self.get_or_create_category("Owoce"),
            'maka': self.get_or_create_category("Mąka i produkty sypkie"),
            'nabial': self.get_or_create_category("Nabiał"),
            'mieso': self.get_or_create_category("Mięso"),
            'przyprawy': self.get_or_create_category("Przyprawy"),
        }
        
        # Pobierz jednostki miary
        units = self.get_measurement_units()
        
        # Dla każdej kategorii utwórz odpowiednią tablicę konwersji
        self.create_vegetables_table(categories['warzywa'], units)
        self.create_fruits_table(categories['owoce'], units)
        self.create_flour_table(categories['maka'], units)
        self.create_dairy_table(categories['nabial'], units)
        self.create_meat_table(categories['mieso'], units)
        self.create_spices_table(categories['przyprawy'], units)
        
        self.stdout.write(self.style.SUCCESS('Utworzono tablice konwersji dla wszystkich głównych kategorii produktów!'))
    
    def get_or_create_category(self, name):
        """Pobierz lub utwórz kategorię składników"""
        category, created = IngredientCategory.objects.get_or_create(name=name)
        if created:
            self.stdout.write(f'Utworzono kategorię: {name}')
        return category
    
    def get_measurement_units(self):
        """Pobierz jednostki miary z bazy danych"""
        units = {}
        for unit in MeasurementUnit.objects.all():
            units[unit.symbol] = unit
        
        # Sprawdź czy istnieją wszystkie potrzebne jednostki
        required_units = ['g', 'kg', 'dag', 'ml', 'l', 'szt', 'łyżka', 'łyżeczka', 'szklanka']
        
        for symbol in required_units:
            if symbol not in units:
                self.stdout.write(self.style.WARNING(f'Brak jednostki {symbol} w bazie danych!'))
        
        return units
    
    def create_or_update_table(self, category, name, is_for_liquids=False):
        """Tworzy lub aktualizuje tablicę konwersji dla kategorii"""
        table, created = ConversionTable.objects.get_or_create(
            name=name,
            category=category,
            defaults={
                'description': f"Standardowa tablica konwersji dla kategorii {category.name}",
                'is_for_liquids': is_for_liquids,
                'is_approved': True
            }
        )
        
        if created:
            self.stdout.write(f'Utworzono tablicę konwersji: {name}')
        else:
            self.stdout.write(f'Aktualizacja istniejącej tablicy: {name}')
            
        return table
    
    def add_conversion(self, table, from_unit, to_unit, ratio):
        """Dodaje przelicznik do tablicy konwersji"""
        entry, created = ConversionTableEntry.objects.get_or_create(
            table=table,
            from_unit=from_unit,
            to_unit=to_unit,
            defaults={
                'ratio': Decimal(str(ratio)),
                'is_exact': True
            }
        )
        return entry
    
    def create_vegetables_table(self, category, units):
        """Tworzy tablicę konwersji dla warzyw"""
        table = self.create_or_update_table(category, "Warzywa ogólne")
        
        # Dodaj standardowe przeliczniki
        if 'g' in units and 'kg' in units:
            self.add_conversion(table, units['g'], units['kg'], 0.001)  # g -> kg
            self.add_conversion(table, units['kg'], units['g'], 1000)    # kg -> g
        
        if 'g' in units and 'dag' in units:
            self.add_conversion(table, units['g'], units['dag'], 0.1)    # g -> dag
            self.add_conversion(table, units['dag'], units['g'], 10)     # dag -> g
        
        if 'szt' in units and 'g' in units:
            # Domyślna waga sztuki warzywa to ok. 150g (średni pomidor/cebula)
            self.add_conversion(table, units['szt'], units['g'], 150)
            self.add_conversion(table, units['g'], units['szt'], 1/150)
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono konfigurację tablicy konwersji dla {category.name}'))
    
    def create_fruits_table(self, category, units):
        """Tworzy tablicę konwersji dla owoców"""
        table = self.create_or_update_table(category, "Owoce ogólne")
        
        # Dodaj standardowe przeliczniki
        if 'g' in units and 'kg' in units:
            self.add_conversion(table, units['g'], units['kg'], 0.001)  # g -> kg
            self.add_conversion(table, units['kg'], units['g'], 1000)    # kg -> g
        
        if 'g' in units and 'dag' in units:
            self.add_conversion(table, units['g'], units['dag'], 0.1)    # g -> dag
            self.add_conversion(table, units['dag'], units['g'], 10)     # dag -> g
        
        if 'szt' in units and 'g' in units:
            # Domyślna waga sztuki owocu to ok. 180g (średnie jabłko)
            self.add_conversion(table, units['szt'], units['g'], 180)
            self.add_conversion(table, units['g'], units['szt'], 1/180)
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono konfigurację tablicy konwersji dla {category.name}'))
    
    def create_flour_table(self, category, units):
        """Tworzy tablicę konwersji dla mąki i produktów sypkich"""
        table = self.create_or_update_table(category, "Mąka i produkty sypkie")
        
        # Dodaj standardowe przeliczniki
        if 'g' in units and 'kg' in units:
            self.add_conversion(table, units['g'], units['kg'], 0.001)  # g -> kg
            self.add_conversion(table, units['kg'], units['g'], 1000)    # kg -> g
        
        if 'g' in units and 'dag' in units:
            self.add_conversion(table, units['g'], units['dag'], 0.1)    # g -> dag
            self.add_conversion(table, units['dag'], units['g'], 10)     # dag -> g
        
        if 'g' in units and 'szklanka' in units:
            # Szklanka mąki to około 130g
            self.add_conversion(table, units['szklanka'], units['g'], 130)
            self.add_conversion(table, units['g'], units['szklanka'], 1/130)
        
        if 'g' in units and 'łyżka' in units:
            # Łyżka mąki to około 10g
            self.add_conversion(table, units['łyżka'], units['g'], 10)
            self.add_conversion(table, units['g'], units['łyżka'], 1/10)
        
        if 'g' in units and 'łyżeczka' in units:
            # Łyżeczka mąki to około 3g
            self.add_conversion(table, units['łyżeczka'], units['g'], 3)
            self.add_conversion(table, units['g'], units['łyżeczka'], 1/3)
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono konfigurację tablicy konwersji dla {category.name}'))
    
    def create_dairy_table(self, category, units):
        """Tworzy tablicę konwersji dla nabiału"""
        table = self.create_or_update_table(category, "Nabiał płynny", is_for_liquids=True)
        
        # Dodaj standardowe przeliczniki
        if 'ml' in units and 'l' in units:
            self.add_conversion(table, units['ml'], units['l'], 0.001)  # ml -> l
            self.add_conversion(table, units['l'], units['ml'], 1000)    # l -> ml
        
        if 'ml' in units and 'g' in units:
            # Mleko i jogurt mają gęstość około 1.03 g/ml
            self.add_conversion(table, units['ml'], units['g'], 1.03)    # ml -> g
            self.add_conversion(table, units['g'], units['ml'], 1/1.03)  # g -> ml
        
        if 'ml' in units and 'szklanka' in units:
            # Szklanka to około 250ml
            self.add_conversion(table, units['szklanka'], units['ml'], 250)
            self.add_conversion(table, units['ml'], units['szklanka'], 1/250)
        
        if 'ml' in units and 'łyżka' in units:
            # Łyżka to około 15ml
            self.add_conversion(table, units['łyżka'], units['ml'], 15)
            self.add_conversion(table, units['ml'], units['łyżka'], 1/15)
        
        if 'ml' in units and 'łyżeczka' in units:
            # Łyżeczka to około 5ml
            self.add_conversion(table, units['łyżeczka'], units['ml'], 5)
            self.add_conversion(table, units['ml'], units['łyżeczka'], 1/5)
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono konfigurację tablicy konwersji dla {category.name} (płyny)'))
        
        # Dodaj osobną tablicę dla serów
        table_cheese = self.create_or_update_table(category, "Sery i produkty stałe")
        
        if 'g' in units and 'kg' in units:
            self.add_conversion(table_cheese, units['g'], units['kg'], 0.001)  # g -> kg
            self.add_conversion(table_cheese, units['kg'], units['g'], 1000)    # kg -> g
        
        if 'g' in units and 'dag' in units:
            self.add_conversion(table_cheese, units['g'], units['dag'], 0.1)    # g -> dag
            self.add_conversion(table_cheese, units['dag'], units['g'], 10)     # dag -> g
        
        if 'g' in units and 'łyżka' in units:
            # Łyżka tartego sera to około 15g
            self.add_conversion(table_cheese, units['łyżka'], units['g'], 15)
            self.add_conversion(table_cheese, units['g'], units['łyżka'], 1/15)
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono konfigurację tablicy konwersji dla {category.name} (produkty stałe)'))
    
    def create_meat_table(self, category, units):
        """Tworzy tablicę konwersji dla mięsa"""
        table = self.create_or_update_table(category, "Mięso ogólne")
        
        # Dodaj standardowe przeliczniki
        if 'g' in units and 'kg' in units:
            self.add_conversion(table, units['g'], units['kg'], 0.001)  # g -> kg
            self.add_conversion(table, units['kg'], units['g'], 1000)    # kg -> g
        
        if 'g' in units and 'dag' in units:
            self.add_conversion(table, units['g'], units['dag'], 0.1)    # g -> dag
            self.add_conversion(table, units['dag'], units['g'], 10)     # dag -> g
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono konfigurację tablicy konwersji dla {category.name}'))
    
    def create_spices_table(self, category, units):
        """Tworzy tablicę konwersji dla przypraw"""
        table = self.create_or_update_table(category, "Przyprawy ogólne")
        
        # Dodaj standardowe przeliczniki
        if 'g' in units and 'kg' in units:
            self.add_conversion(table, units['g'], units['kg'], 0.001)  # g -> kg
            self.add_conversion(table, units['kg'], units['g'], 1000)    # kg -> g
        
        if 'g' in units and 'dag' in units:
            self.add_conversion(table, units['g'], units['dag'], 0.1)    # g -> dag
            self.add_conversion(table, units['dag'], units['g'], 10)     # dag -> g
        
        if 'g' in units and 'łyżka' in units:
            # Łyżka przyprawy to około 5g (zależy od gęstości)
            self.add_conversion(table, units['łyżka'], units['g'], 5)
            self.add_conversion(table, units['g'], units['łyżka'], 1/5)
        
        if 'g' in units and 'łyżeczka' in units:
            # Łyżeczka przyprawy to około 2g
            self.add_conversion(table, units['łyżeczka'], units['g'], 2)
            self.add_conversion(table, units['g'], units['łyżeczka'], 1/2)
        
        self.stdout.write(self.style.SUCCESS(f'Zakończono konfigurację tablicy konwersji dla {category.name}')) 