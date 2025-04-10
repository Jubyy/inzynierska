from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from recipes.models import Ingredient, MeasurementUnit, IngredientCategory, Recipe, RecipeIngredient, UnitConversion
from django.db import transaction
import random
from datetime import timedelta
from django.db.models import Q

User = get_user_model()

# Lista jednostek miary
UNITS = [
    {"name": "gram", "symbol": "g", "is_primary": True},
    {"name": "kilogram", "symbol": "kg", "is_primary": False, "conversion_factor": 1000, "base_unit": "gram"},
    {"name": "dekagram", "symbol": "dag", "is_primary": False, "conversion_factor": 10, "base_unit": "gram"},
    {"name": "mililitr", "symbol": "ml", "is_primary": True},
    {"name": "litr", "symbol": "l", "is_primary": False, "conversion_factor": 1000, "base_unit": "mililitr"},
    {"name": "łyżka", "symbol": "łyżka", "is_primary": False, "conversion_factor": 15, "base_unit": "mililitr"},
    {"name": "łyżeczka", "symbol": "łyżeczka", "is_primary": False, "conversion_factor": 5, "base_unit": "mililitr"},
    {"name": "szklanka", "symbol": "szklanka", "is_primary": False, "conversion_factor": 250, "base_unit": "mililitr"},
    {"name": "sztuka", "symbol": "szt.", "is_primary": True},
    {"name": "opakowanie", "symbol": "opak.", "is_primary": False, "base_unit": "sztuka"},
    {"name": "szczypta", "symbol": "szczypta", "is_primary": True},
    {"name": "plaster", "symbol": "plaster", "is_primary": True},
    {"name": "garść", "symbol": "garść", "is_primary": True},
]

# Lista kategorii składników
CATEGORIES = [
    {"name": "Nabiał", "is_vegetarian": True, "is_vegan": False},
    {"name": "Mięso", "is_vegetarian": False, "is_vegan": False},
    {"name": "Warzywa", "is_vegetarian": True, "is_vegan": True},
    {"name": "Owoce", "is_vegetarian": True, "is_vegan": True},
    {"name": "Pieczywo", "is_vegetarian": True, "is_vegan": True},
    {"name": "Przyprawy", "is_vegetarian": True, "is_vegan": True},
    {"name": "Zboża i kasze", "is_vegetarian": True, "is_vegan": True},
    {"name": "Makarony", "is_vegetarian": True, "is_vegan": True},
    {"name": "Ryby i owoce morza", "is_vegetarian": False, "is_vegan": False},
    {"name": "Oleje i tłuszcze", "is_vegetarian": True, "is_vegan": True},
    {"name": "Słodycze", "is_vegetarian": True, "is_vegan": False},
    {"name": "Napoje", "is_vegetarian": True, "is_vegan": True},
    {"name": "Bakalie", "is_vegetarian": True, "is_vegan": True},
    {"name": "Przetwory", "is_vegetarian": True, "is_vegan": True},
    {"name": "Inne", "is_vegetarian": True, "is_vegan": True},
]

# Lista składników podzielona na kategorie
INGREDIENTS = {
    "Nabiał": [
        "Mleko", "Śmietana 18%", "Śmietana 30%", "Śmietana 12%", "Jogurt naturalny", 
        "Jogurt grecki", "Kefir", "Maślanka", "Ser żółty", "Ser pleśniowy", 
        "Ser feta", "Ser mozzarella", "Ser ricotta", "Twaróg", "Jajka", 
        "Masło", "Margaryna", "Serek mascarpone", "Serek homogenizowany", "Serek wiejski",
        "Parmezan", "Ser kozi", "Ser owczy", "Ser topiony", "Ser camembert",
        "Ser brie", "Ser cheddar", "Śmietanka do kawy", "Mleko kokosowe", "Mleko migdałowe",
        "Mleko owsiane", "Mleko ryżowe", "Mleko sojowe", "Jogurt owocowy", "Jogurt waniliowy",
        "Jogurt kawowy", "Jogurt kokosowy", "Serek waniliowy", "Serek czekoladowy", "Serek truskawkowy"
    ],
    "Mięso": [
        "Kurczak", "Indyk", "Wołowina", "Wieprzowina", "Cielęcina", 
        "Jagnięcina", "Królik", "Kaczka", "Gęś", "Pierś z kurczaka", 
        "Udziec kurczaka", "Skrzydełka kurczaka", "Filet z indyka", "Mięso mielone", "Wątróbka",
        "Żeberka", "Golonka", "Karkówka", "Schab", "Polędwica wołowa",
        "Boczek", "Szynka", "Kiełbasa", "Parówki", "Salami",
        "Kabanosy", "Mortadela", "Pasztet", "Metka", "Chorizo",
        "Pepperoni", "Łopatka wieprzowa", "Łopatka wołowa", "Roastbeef", "Antrykot",
        "Rostbef", "Krówka wołowa", "Ozorki", "Nerki", "Flaki"
    ],
    "Warzywa": [
        "Pomidor", "Ogórek", "Marchew", "Pietruszka", "Seler", 
        "Por", "Cebula", "Czosnek", "Ziemniaki", "Bataty", 
        "Papryka czerwona", "Papryka żółta", "Papryka zielona", "Kukurydza", "Groszek", 
        "Fasola czerwona", "Fasola biała", "Fasola szparagowa", "Soczewica", "Brokuł",
        "Kalafior", "Kapusta biała", "Kapusta czerwona", "Kapusta pekińska", "Rzodkiewka",
        "Cukinia", "Bakłażan", "Szpinak", "Sałata", "Rukola",
        "Roszponka", "Botwina", "Burak", "Dynia", "Pieczarki",
        "Awokado", "Szparagi", "Karczochy", "Szczypiorek", "Koperek",
        "Bazylia", "Lubczyk", "Tymianek", "Rozmaryn", "Imbir",
        "Chrzan", "Jarmuż", "Rabarbar", "Kiełki", "Tofu"
    ],
    "Owoce": [
        "Jabłko", "Gruszka", "Śliwka", "Brzoskwinia", "Nektarynka", 
        "Morela", "Wiśnia", "Czereśnia", "Banan", "Kiwi", 
        "Truskawka", "Malina", "Jeżyna", "Borówka", "Porzeczka", 
        "Agrest", "Ananas", "Mango", "Papaja", "Granat",
        "Kokos", "Cytryna", "Limonka", "Pomarańcza", "Grejpfrut",
        "Mandarynka", "Arbuz", "Melon", "Liczi", "Marakuja",
        "Karambola", "Persymona", "Figa", "Daktyl", "Kumkwat",
        "Awokado", "Winogrona", "Śliwki suszone", "Morele suszone", "Rodzynki",
        "Żurawina suszona", "Jagody goji", "Acai", "Pitaja", "Miechunka"
    ],
    "Pieczywo": [
        "Chleb pszenny", "Chleb żytni", "Chleb razowy", "Chleb graham", "Chleb tostowy", 
        "Bułka", "Bagietka", "Rogal", "Croissant", "Ciabatta", 
        "Focaccia", "Pita", "Tortilla", "Naan", "Pumpernikiel",
        "Chleb bezglutenowy", "Chleb orkiszowy", "Chleb na zakwasie", "Bułka grahamka", "Precel",
        "Bajgiel", "Chałka", "Bułka maślana", "Bułka słodka", "Drożdżówka",
        "Pączek", "Oponka", "Grzanka", "Suchary", "Bułka tarta",
        "Brioszka", "Maca", "Chleb na parze", "Grissini", "Bułka z makiem",
        "Tosty", "Podpłomyk", "Chleb kukurydziany", "Obwarzanek", "Paluszki"
    ],
    "Przyprawy": [
        "Sól", "Pieprz czarny", "Pieprz biały", "Pieprz kolorowy", "Pieprz cayenne", 
        "Papryka słodka", "Papryka ostra", "Kurkuma", "Curry", "Cynamon", 
        "Imbir", "Gałka muszkatołowa", "Kardamon", "Ziele angielskie", "Liść laurowy",
        "Oregano", "Bazylia", "Tymianek", "Majeranek", "Rozmaryn",
        "Kminek", "Kolendra", "Kmin rzymski", "Szafran", "Wanilia",
        "Anyż", "Goździki", "Cząber", "Lubczyk", "Estragon",
        "Jałowiec", "Sumak", "Krokosz", "Lawenda", "Melisa",
        "Mięta", "Szałwia", "Werbena", "Trawa cytrynowa", "Gorczyca",
        "Kozieradka", "Asafetyda", "Kurkumina", "Chili", "Piment"
    ],
    "Zboża i kasze": [
        "Ryż biały", "Ryż brązowy", "Ryż jaśminowy", "Ryż basmati", "Ryż dziki", 
        "Kasza gryczana", "Kasza jęczmienna", "Kasza jaglana", "Kasza manna", "Kasza kukurydziana", 
        "Komosa ryżowa", "Bulgur", "Kuskus", "Owsianka", "Płatki owsiane",
        "Płatki jęczmienne", "Płatki jaglane", "Musli", "Granola", "Otręby",
        "Mąka pszenna", "Mąka razowa", "Mąka żytnia", "Mąka kukurydziana", "Mąka ryżowa",
        "Mąka orkiszowa", "Mąka gryczana", "Mąka owsiana", "Mąka ziemniaczana", "Skrobia kukurydziana",
        "Amarantus", "Sorgo", "Proso", "Pszenica orkisz", "Pszenica kamut",
        "Żyto", "Jęczmień", "Orkisz", "Pszenżyto", "Millet"
    ],
    "Makarony": [
        "Makaron spaghetti", "Makaron tagliatelle", "Makaron penne", "Makaron farfalle", "Makaron fusilli", 
        "Makaron cannelloni", "Makaron lasagne", "Makaron rurki", "Makaron nitki", "Makaron ryżowy", 
        "Makaron udon", "Makaron soba", "Makaron ramen", "Makaron jajeczny", "Makaron bezglutenowy",
        "Makaron pełnoziarnisty", "Makaron orkiszowy", "Makaron gryczany", "Makaron kukurydziany", "Makaron z ciecierzycy",
        "Makaron z soczewicy", "Makaron z grochu", "Makaron z fasoli", "Makaron z amarantusa", "Makaron z komosy ryżowej",
        "Makaron z quinoa", "Makaron ze spiruliny", "Makaron z alg", "Makaron z kaszy jaglanej", "Makaron z kaszy gryczanej"
    ],
    "Ryby i owoce morza": [
        "Łosoś", "Dorsz", "Tuńczyk", "Pstrąg", "Makrela", 
        "Śledź", "Halibut", "Tilapia", "Sandacz", "Karp", 
        "Mintaj", "Morszczuk", "Sola", "Flądra", "Krewetki",
        "Kalmary", "Ośmiornica", "Małże", "Ostrygi", "Homary",
        "Kraby", "Langusta", "Raki", "Węgorz", "Sardynka",
        "Szprot", "Płoć", "Szczupak", "Sum", "Okoń",
        "Karaś", "Gładzica", "Dorada", "Barramundi", "Panga",
        "Ikra", "Kawior", "Wątróbka z dorsza", "Ryby wędzone", "Konserwy rybne"
    ],
    "Oleje i tłuszcze": [
        "Olej rzepakowy", "Olej słonecznikowy", "Olej oliwkowy", "Olej kokosowy", "Olej lniany", 
        "Olej sezamowy", "Olej z pestek winogron", "Olej arachidowy", "Olej dyniowy", "Olej rydzowy", 
        "Masło", "Masło klarowane", "Smalec", "Margaryna", "Tłuszcz piekarski",
        "Olej kukurydziany", "Olej z orzechów włoskich", "Olej z awokado", "Olej z pestek moreli", "Olej z orzechów laskowych",
        "Olej z czarnuszki", "Olej z wiesiołka", "Olej z ogórecznika", "Olej rybi", "Olej palmowy"
    ],
    "Słodycze": [
        "Czekolada", "Batony", "Cukierki", "Żelki", "Herbatniki", 
        "Wafle", "Ciastka", "Lizaki", "Lody", "Guma do żucia", 
        "Miód", "Dżem", "Nutella", "Krówki", "Ptasie mleczko",
        "Torty", "Ciasta", "Pierniki", "Marcepan", "Chałwa",
        "Beza", "Karmel", "Pralinki", "Trufle", "Toffi",
        "Pianki", "Lukrecja", "Galaretki", "Rachatłukum", "Ciasto francuskie",
        "Rogaliki", "Praliny", "Sernik", "Szarlotka", "Makowiec",
        "Babka", "Pączki", "Drożdżówki", "Rurki z kremem", "Eklerki",
        "Bezy", "Croissanty", "Napoleonka", "Murzynek", "Delicje",
        "Mazurki", "Sękacz", "Chałwa", "Krówki", "Michałki"
    ],
    "Napoje": [
        "Woda", "Herbata", "Kawa", "Sok pomarańczowy", "Sok jabłkowy", 
        "Sok pomidorowy", "Sok z czarnej porzeczki", "Lemoniada", "Cola", "Sprite", 
        "Piwo", "Wino", "Wódka", "Whisky", "Rum",
        "Gin", "Tequila", "Koniak", "Likier", "Kompot",
        "Smoothie", "Kakao", "Gorąca czekolada", "Shake", "Mleko",
        "Kefir", "Jogurt pitny", "Maślanka", "Woda kokosowa", "Syrop owocowy",
        "Nektar", "Napój energetyczny", "Napój izotoniczny", "Napój gazowany", "Napój niegazowany"
    ],
    "Bakalie": [
        "Migdały", "Orzechy włoskie", "Orzechy laskowe", "Orzechy nerkowca", "Orzechy brazylijskie", 
        "Orzechy pistacjowe", "Orzechy ziemne", "Orzechy makadamia", "Orzechy pekan", "Rodzynki", 
        "Morele suszone", "Śliwki suszone", "Figi suszone", "Daktyle", "Żurawina suszona",
        "Wiórki kokosowe", "Chipsy bananowe", "Chipsy jabłkowe", "Jagody goji", "Nasiona chia",
        "Nasiona słonecznika", "Nasiona dyni", "Nasiona lnu", "Nasiona sezamu", "Nasiona konopi",
        "Nasiona maku", "Pestki moreli", "Pestki dyni", "Pestki arbuza", "Mieszanka studencka"
    ],
    "Przetwory": [
        "Ketchup", "Musztarda", "Majonez", "Ocet", "Sos sojowy", 
        "Sos worcestershire", "Sos tabasco", "Koncentrat pomidorowy", "Dżem truskawkowy", "Dżem morelowy", 
        "Dżem wiśniowy", "Dżem z czarnej porzeczki", "Konfitura", "Marmolada", "Powidła",
        "Miód", "Syrop klonowy", "Syrop z agawy", "Mleko zagęszczone", "Mleko w proszku",
        "Groszek konserwowy", "Kukurydza konserwowa", "Fasola konserwowa", "Oliwki", "Kapary",
        "Suszone pomidory", "Kiszone ogórki", "Kiszona kapusta", "Marynowane pieczarki", "Marynowana papryka",
        "Pesto", "Hummus", "Guacamole", "Salsa", "Bułka tarta",
        "Panko", "Grzyby suszone", "Papryka suszona", "Zioła suszone", "Bulion"
    ],
    "Inne": [
        "Drożdże", "Proszek do pieczenia", "Soda oczyszczona", "Guma ksantanowa", "Agar", 
        "Żelatyna", "Pektyna", "Kakao", "Karob", "Lecytyna", 
        "Esencja waniliowa", "Esencja migdałowa", "Esencja rumowa", "Spirytus", "Ekstrakt słodowy",
        "Kminek", "Anyż", "Imbir", "Kardamon", "Kurkuma",
        "Szafran", "Wanilia", "Cynamon", "Goździki", "Kolendra",
        "Bazylia", "Oregano", "Rozmaryn", "Tymianek", "Majeranek",
        "Koper", "Pietruszka", "Szczypiorek", "Lubczyk", "Estragon",
        "Szałwia", "Mięta", "Melisa", "Rukiew wodna", "Rukola"
    ]
}

# Lista gotowych przepisów
RECIPES = [
    {
        "title": "Spaghetti Bolognese",
        "description": "Klasyczne włoskie danie z makaronem i sosem mięsnym",
        "time": 45,
        "servings": 4,
        "difficulty": "easy",
        "instructions": "1. Cebulę i czosnek posiekać, marchewkę i selera zetrzeć na tarce.\n2. Na patelni rozgrzać oliwę, zeszklić cebulę i czosnek.\n3. Dodać mięso mielone, smażyć rozbijając grudki.\n4. Dodać marchewkę i selera, smażyć 5 minut.\n5. Wlać wino, gotować 2 minuty.\n6. Dodać pomidory, koncentrat, zioła, gotować 30 minut.\n7. Ugotować makaron al dente.\n8. Podawać makaron z sosem, posypany parmezanem.",
        "ingredients": [
            {"name": "Makaron spaghetti", "amount": 400, "unit": "gram"},
            {"name": "Mięso mielone", "amount": 500, "unit": "gram"},
            {"name": "Cebula", "amount": 1, "unit": "sztuka"},
            {"name": "Czosnek", "amount": 2, "unit": "sztuka"},
            {"name": "Marchew", "amount": 1, "unit": "sztuka"},
            {"name": "Seler", "amount": 100, "unit": "gram"},
            {"name": "Pomidory krojone", "amount": 400, "unit": "gram"},
            {"name": "Koncentrat pomidorowy", "amount": 2, "unit": "łyżka"},
            {"name": "Czerwone wino", "amount": 100, "unit": "mililitr"},
            {"name": "Oregano", "amount": 1, "unit": "łyżeczka"},
            {"name": "Bazylia", "amount": 1, "unit": "łyżeczka"},
            {"name": "Oliwa z oliwek", "amount": 2, "unit": "łyżka"},
            {"name": "Parmezan", "amount": 50, "unit": "gram"}
        ]
    },
    {
        "title": "Placki ziemniaczane",
        "description": "Tradycyjne polskie placki z tartych ziemniaków",
        "time": 30,
        "servings": 4,
        "difficulty": "easy",
        "instructions": "1. Ziemniaki obrać i zetrzeć na tarce o drobnych oczkach.\n2. Cebulę zetrzeć na tarce.\n3. Dodać jajko, mąkę, sól i pieprz.\n4. Dokładnie wymieszać.\n5. Smażyć na rozgrzanym oleju małe porcje ciasta.\n6. Gdy się zarumienią z jednej strony, przewrócić.\n7. Odsączyć na papierowym ręczniku.\n8. Podawać ze śmietaną lub gulaszem.",
        "ingredients": [
            {"name": "Ziemniaki", "amount": 1, "unit": "kilogram"},
            {"name": "Cebula", "amount": 1, "unit": "sztuka"},
            {"name": "Jajka", "amount": 1, "unit": "sztuka"},
            {"name": "Mąka pszenna", "amount": 3, "unit": "łyżka"},
            {"name": "Olej", "amount": 100, "unit": "mililitr"},
            {"name": "Sól", "amount": 1, "unit": "łyżeczka"},
            {"name": "Pieprz czarny", "amount": 1, "unit": "szczypta"}
        ]
    }
]

class Command(BaseCommand):
    help = 'Wypełnia bazę danych przykładowymi danymi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ingredients',
            type=int,
            default=300,
            help='Liczba składników do utworzenia'
        )
        parser.add_argument(
            '--recipes',
            type=int,
            default=25,
            help='Liczba przepisów do utworzenia'
        )

    def handle(self, *args, **options):
        # Sprawdź, czy istnieje użytkownik
        users = User.objects.all()
        if not users.exists():
            self.stdout.write(self.style.ERROR('Brak użytkowników w bazie danych. Dodaj najpierw użytkownika.'))
            return
        
        # Pobierz pierwszego użytkownika
        user = users.first()
        
        with transaction.atomic():
            # 1. Tworzenie jednostek miary
            units = self._create_units()
            self.stdout.write(self.style.SUCCESS(f'Utworzono {len(units)} jednostek miary'))
        
            # 2. Tworzenie kategorii składników
            categories = self._create_ingredient_categories()
            self.stdout.write(self.style.SUCCESS(f'Utworzono {len(categories)} kategorii składników'))
        
            # 3. Tworzenie składników
            ingredients = self._create_ingredients(options['ingredients'], categories, units)
            self.stdout.write(self.style.SUCCESS(f'Utworzono {len(ingredients)} składników'))
            
            # 4. Tworzenie przepisów
            recipes = self._create_recipes(options['recipes'], user, ingredients, units)
            self.stdout.write(self.style.SUCCESS(f'Utworzono {len(recipes)} przepisów'))

        self.stdout.write(self.style.SUCCESS('Inicjalizacja bazy danych zakończona pomyślnie!'))

    def _create_units(self):
        """Tworzy jednostki miary"""
        units_dict = {}  # Słownik do przechowywania jednostek dla konwersji
        
        # Najpierw tworzenie podstawowych jednostek
        for unit_data in UNITS:
            if unit_data.get('is_primary', False):
                unit = MeasurementUnit.objects.get_or_create(
                    name=unit_data['name'],
                    defaults={
                        'symbol': unit_data['symbol'],
                        'is_base': True
                    }
                )[0]
                units_dict[unit_data['name']] = unit
        
        # Następnie tworzenie jednostek z konwersją
        for unit_data in UNITS:
            if not unit_data.get('is_primary', False):
                base_unit_name = unit_data.get('base_unit')
                base_unit = units_dict.get(base_unit_name)
                
                if base_unit:
                    unit = MeasurementUnit.objects.get_or_create(
                        name=unit_data['name'],
                        defaults={
                            'symbol': unit_data['symbol'],
                            'is_base': False
                        }
                    )[0]
                    units_dict[unit_data['name']] = unit
                    
                    # Tworzymy konwersję między jednostkami
                    conversion_factor = unit_data.get('conversion_factor', 1)
                    UnitConversion.objects.get_or_create(
                        from_unit=unit,
                        to_unit=base_unit,
                        defaults={
                            'ratio': conversion_factor
                        }
                    )
                    
                    # Tworzymy też odwrotną konwersję
                    UnitConversion.objects.get_or_create(
                        from_unit=base_unit,
                        to_unit=unit,
                        defaults={
                            'ratio': 1.0 / conversion_factor
                        }
                    )
        
        return MeasurementUnit.objects.all()

    def _create_ingredient_categories(self):
        """Tworzy kategorie składników"""
        categories = []
        for category_data in CATEGORIES:
            category = IngredientCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'is_vegetarian': category_data.get('is_vegetarian', True),
                    'is_vegan': category_data.get('is_vegan', False)
                }
            )[0]
            categories.append(category)
        return categories

    def _create_ingredients(self, count, categories, units):
        """Tworzy składniki"""
        ingredients = []
        
        # Zbieram wszystkie nazwy składników z listy INGREDIENTS
        all_ingredient_names = []
        for category_name, ingredients_list in INGREDIENTS.items():
            all_ingredient_names.extend(ingredients_list)
        
        # Jeśli mamy za mało składników na liście, to generujemy dodatkowe nazwy
        if len(all_ingredient_names) < count:
            self.stdout.write(self.style.WARNING(f'Za mało składników na liście, generuję dodatkowe nazwy...'))
            extra_needed = count - len(all_ingredient_names)
            for i in range(extra_needed):
                all_ingredient_names.append(f"Składnik #{i+1}")
        
        # Używam każdej nazwy tylko raz
        used_names = set()
        
        # Podstawowe jednostki
        gram_unit = MeasurementUnit.objects.get(name='gram')
        mililitr_unit = MeasurementUnit.objects.get(name='mililitr')
        sztuka_unit = MeasurementUnit.objects.get(name='sztuka')
        
        # Dla każdej kategorii, dodajemy jej składniki
        for category_name, ingredients_list in INGREDIENTS.items():
            # Znajdź odpowiednią kategorię
            category = next((c for c in categories if c.name == category_name), None)
            if not category:
                category = categories[0]
            
            # Dodaj składniki z tej kategorii
            for ingredient_name in ingredients_list:
                if ingredient_name in used_names:
                    continue
                
                if len(ingredients) >= count:
                    break
                
                # Wybierz domyślną jednostkę dla tego składnika
                if 'Mąka' in ingredient_name or 'Kasza' in ingredient_name or 'Ryż' in ingredient_name or 'Mięso' in ingredient_name:
                    default_unit = gram_unit
                elif 'Mleko' in ingredient_name or 'Sok' in ingredient_name or 'Woda' in ingredient_name or 'Olej' in ingredient_name:
                    default_unit = mililitr_unit
                elif 'Jajka' in ingredient_name or any(fruit in ingredient_name for fruit in ['Jabłko', 'Gruszka', 'Pomarańcza']):
                    default_unit = sztuka_unit
                else:
                    # Losowo wybierz jednostkę
                    default_unit = random.choice([gram_unit, mililitr_unit, sztuka_unit])
                
                # Utwórz składnik
                ingredient = Ingredient.objects.get_or_create(
                    name=ingredient_name,
                    defaults={
                        'category': category,
                        'default_unit': default_unit,
                    }
                )[0]
                
                # Dodaj kompatybilne jednostki
                # Dla wagi
                if default_unit == gram_unit:
                    weight_units = MeasurementUnit.objects.filter(
                        Q(name='gram') | Q(name='kilogram') | Q(name='dekagram')
                    )
                    for unit in weight_units:
                        ingredient.compatible_units.add(unit)
                
                # Dla objętości
                elif default_unit == mililitr_unit:
                    volume_units = MeasurementUnit.objects.filter(
                        Q(name='mililitr') | Q(name='litr') | Q(name='łyżka') | 
                        Q(name='łyżeczka') | Q(name='szklanka')
                    )
                    for unit in volume_units:
                        ingredient.compatible_units.add(unit)
                
                # Dla sztuk
                elif default_unit == sztuka_unit:
                    piece_units = MeasurementUnit.objects.filter(
                        Q(name='sztuka') | Q(name='opakowanie')
                    )
                    for unit in piece_units:
                        ingredient.compatible_units.add(unit)
                
                ingredients.append(ingredient)
                used_names.add(ingredient_name)
                
                if len(ingredients) >= count:
                    break
        
        self.stdout.write(self.style.SUCCESS(f'Utworzono {len(ingredients)} składników'))
        return ingredients
        
    def _create_recipes(self, count, user, ingredients, units):
        """Tworzy przepisy"""
        recipes = []
        
        # Najpierw dodajemy gotowe przepisy
        for recipe_data in RECIPES:
            recipe = Recipe.objects.get_or_create(
                author=user,
                title=recipe_data['title'],
                defaults={
                    'description': recipe_data['description'],
                    'preparation_time': recipe_data['time'],
                    'servings': recipe_data['servings'],
                    'difficulty': recipe_data['difficulty'],
                    'instructions': recipe_data['instructions'],
                    'is_public': True
                }
            )[0]
            
            # Czyszczenie istniejących składników
            RecipeIngredient.objects.filter(recipe=recipe).delete()
            
            # Dodawanie składników
            for i, ingredient_data in enumerate(recipe_data['ingredients']):
                # Znajdź odpowiedni składnik
                ingredient_name = ingredient_data['name']
                ingredient = next((i for i in ingredients if i.name == ingredient_name), None)
                
                # Jeśli nie znaleziono, weź pierwszy lepszy z listy
                if not ingredient and ingredients:
                    ingredient = ingredients[0]
                
                # Znajdź jednostkę
                unit_name = ingredient_data['unit']
                unit = next((u for u in units if u.name == unit_name), None)
                
                # Jeśli nie znaleziono, użyj domyślnej jednostki składnika
                if not unit and ingredient and ingredient.default_unit:
                    unit = ingredient.default_unit
                
                # Jeśli mamy składnik i jednostkę, dodajemy do przepisu
                if ingredient and unit:
                    # Sprawdź czy ten składnik już istnieje w przepisie (unikaj duplikatów)
                    if not RecipeIngredient.objects.filter(recipe=recipe, ingredient=ingredient).exists():
                        RecipeIngredient.objects.create(
                            recipe=recipe,
                            ingredient=ingredient,
                            amount=ingredient_data['amount'],
                            unit=unit
                        )
            
            recipes.append(recipe)
        
        # Generowanie dodatkowych przepisów
        recipe_names = [
            "Omlet z warzywami", "Sałatka grecka", "Risotto grzybowe", "Kotlety schabowe", 
            "Lasagne", "Kurczak curry", "Zupa pomidorowa", "Gulasz wołowy", 
            "Naleśniki z serem", "Pizza domowa", "Pierogi ruskie", "Bigos", 
            "Krupnik", "Gołąbki", "Chili con carne", "Sałatka cezar", 
            "Zupa ogórkowa", "Knedle ze śliwkami", "Babka wielkanocna", "Sernik", 
            "Szarlotka", "Rosół", "Żurek", "Kotlet mielony", 
            "Sałatka jarzynowa", "Karkówka z grilla", "Jajecznica", "Leczo", 
            "Zupa szczawiowa", "Gofry", "Racuchy", "Zupa pieczarkowa", 
            "Kopytka", "Ciasto drożdżowe", "Pasztet", "Kotlety mielone",
            "Kapuśniak", "Kluski śląskie", "Zupa cebulowa", "Fasolka po bretońsku",
            "Placki z jabłkami", "Rurki z kremem", "Kotlety rybne", "Surówka z marchewki",
            "Mizeria", "Kompot owocowy", "Kisiel", "Budyń", "Rogaliki drożdżowe"
        ]
        
        while len(recipes) < count and recipe_names:
            recipe_name = recipe_names.pop(0)
            
            # Losowe dane dla przepisu
            difficulty_choices = ['easy', 'medium', 'hard']
            recipe = Recipe.objects.get_or_create(
                author=user,
                title=recipe_name,
                defaults={
                    'description': f"Przepis na {recipe_name.lower()}",
                    'preparation_time': random.randint(15, 120),
                    'servings': random.randint(2, 8),
                    'difficulty': random.choice(difficulty_choices),
                    'instructions': f"Instrukcje przygotowania {recipe_name.lower()}:\n1. Przygotuj składniki\n2. Wymieszaj wszystko\n3. Ugotuj/usmaż/upiecz\n4. Podawaj",
                    'is_public': True
                }
            )[0]
            
            # Czyszczenie istniejących składników
            RecipeIngredient.objects.filter(recipe=recipe).delete()
            
            # Dodawanie składników (od 3 do 10)
            ingredient_count = random.randint(3, 10)
            selected_ingredients = random.sample(list(ingredients), min(ingredient_count, len(ingredients)))
            
            for i, ingredient in enumerate(selected_ingredients):
                # Wybierz jednostkę z kompatybilnych lub domyślną
                unit = ingredient.default_unit
                if ingredient.compatible_units.exists():
                    unit = random.choice(list(ingredient.compatible_units.all()))
                
                # Losowa ilość
                if unit.name == 'sztuka':
                    amount = random.randint(1, 10)
                elif unit.name == 'kilogram' or unit.name == 'litr':
                    amount = round(random.uniform(0.1, 2.0), 1)
                elif unit.name in ['łyżka', 'łyżeczka', 'szczypta']:
                    amount = random.randint(1, 5)
                else:
                    amount = random.randint(10, 500)
                
                # Jeśli mamy składnik i jednostkę, dodajemy do przepisu
                # Upewnij się, że ten składnik jeszcze nie istnieje w przepisie
                if not RecipeIngredient.objects.filter(recipe=recipe, ingredient=ingredient).exists():
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=amount,
                        unit=unit
                    )
            
            recipes.append(recipe)
        
        return recipes 