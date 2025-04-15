from django.core.management.base import BaseCommand
from recipes.models import Ingredient

class Command(BaseCommand):
    help = 'Aktualizuje wagi sztuk dla istniejących składników'

    def handle(self, *args, **options):
        # Słownik typowych wag dla popularnych produktów (w gramach)
        typical_weights = {
            'pomidor': 150,
            'pomidory': 150,
            'cebula': 110,
            'ziemniak': 170,
            'ziemniaki': 170,
            'marchew': 80,
            'marchewka': 80,
            'jabłko': 180,
            'jabłka': 180,
            'pomarańcza': 200,
            'pomarańcze': 200,
            'cytryna': 70,
            'cytryny': 70,
            'ogórek': 200,
            'ogórki': 200,
            'papryka': 160,
            'czosnek': 5,  # ząbek czosnku
            'jajko': 60,
            'jajka': 60,
            'jaja': 60,
            'banan': 120,
            'banany': 120,
            'gruszka': 170,
            'gruszki': 170,
            'pietruszka': 60,
            'bakłażan': 300,
            'cukinia': 250,
            'por': 100,
            'pory': 100,
            'brokuł': 400,
            'brokuły': 400,
            'kalafior': 800,
            'kalafiory': 800,
            'malina': 6,
            'maliny': 6,
            'truskawka': 15,
            'truskawki': 15,
            'winogrono': 8,
            'winogrona': 8,
            'kapusta': 900,
            'seler': 350,
            'grzyb': 25,
            'grzyby': 25,
            'chleb': 500,  # Waga bochenka
        }
        
        # Mapowanie specyficznych ID składników do ich wag
        specific_ingredients = {
            3: 15,   # Truskawki - 15g/sztuka
            17: 500, # Chleb pszenny - 500g/bochenek
            37: 350, # Seler - 350g
            46: 900, # Kapusta - 900g
            48: 25,  # Grzyby - 25g
        }
        
        # Liczniki dla statystyk
        updated_count = 0
        already_set_count = 0
        no_match_count = 0
        
        # Pobierz wszystkie składniki, które mogą być mierzone w sztukach i nie mają ustawionej wagi
        ingredients_to_update = Ingredient.objects.filter(
            unit_type__contains='piece'
        )
        
        self.stdout.write(f"Znaleziono {ingredients_to_update.count()} składników, które mogą być mierzone w sztukach")
        
        # Aktualizuj składniki według specyficznego ID
        for ingredient_id, weight in specific_ingredients.items():
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
                if 'piece' in ingredient.unit_type and not ingredient.piece_weight:
                    ingredient.piece_weight = weight
                    ingredient.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Zaktualizowano wagę dla składnika {ingredient.name} (id: {ingredient.id}): {weight}g"))
                    updated_count += 1
            except Ingredient.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"! Nie znaleziono składnika o id={ingredient_id}"))
        
        # Aktualizuj pozostałe składniki
        for ingredient in ingredients_to_update:
            # Pomijamy składniki, które już mają wagę
            if ingredient.piece_weight:
                already_set_count += 1
                continue
                
            # Próbujemy dopasować nazwę składnika do typowych wag
            matched = False
            for product, weight in typical_weights.items():
                if product.lower() in ingredient.name.lower():
                    ingredient.piece_weight = weight
                    ingredient.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Zaktualizowano wagę dla składnika {ingredient.name} (id: {ingredient.id}): {weight}g"))
                    updated_count += 1
                    matched = True
                    break
            
            if not matched:
                self.stdout.write(self.style.WARNING(
                    f"! Nie znaleziono pasującej wagi dla {ingredient.name} (id: {ingredient.id})"))
                no_match_count += 1
        
        # Wyświetl podsumowanie
        self.stdout.write("\nPodsumowanie aktualizacji:")
        self.stdout.write(f"- Zaktualizowano: {updated_count} składników")
        self.stdout.write(f"- Już miało ustawioną wagę: {already_set_count} składników")
        self.stdout.write(f"- Bez dopasowania: {no_match_count} składników") 