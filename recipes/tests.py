from django.test import TestCase
from django.contrib.auth.models import User
from recipes.models import Recipe, RecipeIngredient, Ingredient, IngredientCategory, MeasurementUnit
from fridge.models import FridgeItem

class RecipeVegetarianTest(TestCase):
    """
    Testy sprawdzające czy przepisy są poprawnie klasyfikowane jako wegetariańskie
    lub niewegetariańskie w zależności od kategorii składników.
    """
    
    def setUp(self):
        # Tworzenie użytkownika testowego
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        
        # Tworzenie kategorii składników
        self.meat_category = IngredientCategory.objects.create(
            name='Mięso',
            is_vegetarian=False,
            is_vegan=False
        )
        
        self.vegetable_category = IngredientCategory.objects.create(
            name='Warzywa',
            is_vegetarian=True,
            is_vegan=True
        )
        
        self.dairy_category = IngredientCategory.objects.create(
            name='Nabiał',
            is_vegetarian=True,
            is_vegan=False
        )
        
        # Tworzenie składników
        self.chicken = Ingredient.objects.create(
            name='Kurczak',
            category=self.meat_category
        )
        
        self.carrot = Ingredient.objects.create(
            name='Marchew',
            category=self.vegetable_category
        )
        
        self.cheese = Ingredient.objects.create(
            name='Ser',
            category=self.dairy_category
        )
        
        # Tworzenie jednostek miary
        self.gram = MeasurementUnit.objects.create(
            name='Gram',
            symbol='g',
            type='weight',
            base_ratio=1.0
        )
        
        # Tworzenie przepisów
        self.meat_recipe = Recipe.objects.create(
            title='Kurczak z marchewką',
            description='Opis dania mięsnego',
            instructions='Instrukcje dla dania mięsnego',
            servings=4,
            preparation_time=30,
            author=self.user
        )
        
        self.vegetarian_recipe = Recipe.objects.create(
            title='Ser z warzywami',
            description='Opis dania wegetariańskiego',
            instructions='Instrukcje dla dania wegetariańskiego',
            servings=2,
            preparation_time=15,
            author=self.user
        )
        
        self.vegan_recipe = Recipe.objects.create(
            title='Sałatka warzywna',
            description='Opis dania wegańskiego',
            instructions='Instrukcje dla dania wegańskiego',
            servings=2,
            preparation_time=10,
            author=self.user
        )
        
        # Dodawanie składników do przepisów
        RecipeIngredient.objects.create(
            recipe=self.meat_recipe,
            ingredient=self.chicken,
            amount=300,
            unit=self.gram
        )
        
        RecipeIngredient.objects.create(
            recipe=self.meat_recipe,
            ingredient=self.carrot,
            amount=200,
            unit=self.gram
        )
        
        RecipeIngredient.objects.create(
            recipe=self.vegetarian_recipe,
            ingredient=self.cheese,
            amount=100,
            unit=self.gram
        )
        
        RecipeIngredient.objects.create(
            recipe=self.vegetarian_recipe,
            ingredient=self.carrot,
            amount=150,
            unit=self.gram
        )
        
        RecipeIngredient.objects.create(
            recipe=self.vegan_recipe,
            ingredient=self.carrot,
            amount=300,
            unit=self.gram
        )
    
    def test_meat_recipe_is_not_vegetarian(self):
        """Test czy przepis mięsny jest poprawnie oznaczony jako niewegetariański"""
        self.assertFalse(self.meat_recipe.is_vegetarian)
        self.assertFalse(self.meat_recipe.is_vegan)
        self.assertTrue(self.meat_recipe.is_meat)
    
    def test_vegetarian_recipe_is_vegetarian(self):
        """Test czy przepis wegetariański jest poprawnie oznaczony"""
        self.assertTrue(self.vegetarian_recipe.is_vegetarian)
        self.assertFalse(self.vegetarian_recipe.is_vegan)
        self.assertFalse(self.vegetarian_recipe.is_meat)
    
    def test_vegan_recipe_is_vegan(self):
        """Test czy przepis wegański jest poprawnie oznaczony jako wegański i wegetariański"""
        self.assertTrue(self.vegan_recipe.is_vegetarian)
        self.assertTrue(self.vegan_recipe.is_vegan)
        self.assertFalse(self.vegan_recipe.is_meat)
    
    def test_changing_ingredient_category_affects_recipe(self):
        """Test czy zmiana klasyfikacji kategorii składnika wpływa na klasyfikację przepisu"""
        # Początkowy stan
        self.assertTrue(self.vegetarian_recipe.is_vegetarian)
        
        # Zmiana kategorii składnika
        self.cheese.category = self.meat_category
        self.cheese.save()
        
        # Sprawdzenie, czy status przepisu się zmienił
        self.assertFalse(self.vegetarian_recipe.is_vegetarian)


class RecipeAvailabilityTest(TestCase):
    """
    Testy sprawdzające czy dostępność składników w lodówce jest poprawnie określana
    i czy przepisy są prawidłowo filtrowane na tej podstawie.
    """
    
    def setUp(self):
        # Tworzenie użytkownika testowego
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        
        # Tworzenie kategorii składników
        self.vegetable_category = IngredientCategory.objects.create(
            name='Warzywa',
            is_vegetarian=True,
            is_vegan=True
        )
        
        self.spice_category = IngredientCategory.objects.create(
            name='Przyprawy',
            is_vegetarian=True,
            is_vegan=True
        )
        
        # Tworzenie składników
        self.potato = Ingredient.objects.create(
            name='Ziemniaki',
            category=self.vegetable_category
        )
        
        self.onion = Ingredient.objects.create(
            name='Cebula',
            category=self.vegetable_category
        )
        
        self.salt = Ingredient.objects.create(
            name='Sól',
            category=self.spice_category
        )
        
        # Tworzenie jednostek miary
        self.gram = MeasurementUnit.objects.create(
            name='Gram',
            symbol='g',
            type='weight',
            base_ratio=1.0
        )
        
        self.piece = MeasurementUnit.objects.create(
            name='Sztuka',
            symbol='szt',
            type='piece',
            base_ratio=1.0
        )
        
        # Tworzenie przepisu
        self.potato_recipe = Recipe.objects.create(
            title='Ziemniaki z cebulą',
            description='Prosty przepis',
            instructions='Instrukcje',
            servings=2,
            preparation_time=20,
            author=self.user
        )
        
        # Dodawanie składników do przepisu
        RecipeIngredient.objects.create(
            recipe=self.potato_recipe,
            ingredient=self.potato,
            amount=500,
            unit=self.gram
        )
        
        RecipeIngredient.objects.create(
            recipe=self.potato_recipe,
            ingredient=self.onion,
            amount=2,
            unit=self.piece
        )
        
        RecipeIngredient.objects.create(
            recipe=self.potato_recipe,
            ingredient=self.salt,
            amount=5,
            unit=self.gram
        )
    
    def test_recipe_not_available_with_empty_fridge(self):
        """Test czy przepis jest niedostępny przy pustej lodówce"""
        # Sprawdzenie dostępności przepisu bez składników w lodówce
        self.assertFalse(self.potato_recipe.can_be_prepared_with_available_ingredients(self.user))
        
        # Sprawdzenie czy lista brakujących składników zawiera wszystkie składniki przepisu
        missing_ingredients = self.potato_recipe.get_missing_ingredients(self.user)
        self.assertEqual(len(missing_ingredients), 3)
    
    def test_recipe_not_available_with_partial_ingredients(self):
        """Test czy przepis jest niedostępny przy częściowo wypełnionej lodówce"""
        # Dodanie niektórych składników do lodówki
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.potato,
            amount=500,
            unit=self.gram
        )
        
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.salt,
            amount=100,
            unit=self.gram
        )
        
        # Sprawdzenie dostępności przepisu
        self.assertFalse(self.potato_recipe.can_be_prepared_with_available_ingredients(self.user))
        
        # Sprawdzenie czy lista brakujących składników zawiera tylko brakujący składnik
        missing_ingredients = self.potato_recipe.get_missing_ingredients(self.user)
        self.assertEqual(len(missing_ingredients), 1)
        self.assertEqual(missing_ingredients[0].ingredient, self.onion)
    
    def test_recipe_available_with_all_ingredients(self):
        """Test czy przepis jest dostępny przy wszystkich składnikach w lodówce"""
        # Dodanie wszystkich składników do lodówki
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.potato,
            amount=500,
            unit=self.gram
        )
        
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.onion,
            amount=2,
            unit=self.piece
        )
        
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.salt,
            amount=100,
            unit=self.gram
        )
        
        # Sprawdzenie dostępności przepisu
        self.assertTrue(self.potato_recipe.can_be_prepared_with_available_ingredients(self.user))
        
        # Sprawdzenie czy lista brakujących składników jest pusta
        missing_ingredients = self.potato_recipe.get_missing_ingredients(self.user)
        self.assertIsNone(missing_ingredients)


class RecipeFilteringTest(TestCase):
    """
    Testy sprawdzające czy przepisy są poprawnie filtrowane na podstawie 
    dostępności składników w lodówce.
    """
    
    def setUp(self):
        # Tworzenie użytkownika testowego
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        
        # Tworzenie kategorii składników
        self.vegetable_category = IngredientCategory.objects.create(
            name='Warzywa',
            is_vegetarian=True,
            is_vegan=True
        )
        
        self.meat_category = IngredientCategory.objects.create(
            name='Mięso',
            is_vegetarian=False,
            is_vegan=False
        )
        
        # Tworzenie składników
        self.potato = Ingredient.objects.create(
            name='Ziemniaki',
            category=self.vegetable_category
        )
        
        self.carrot = Ingredient.objects.create(
            name='Marchew',
            category=self.vegetable_category
        )
        
        self.chicken = Ingredient.objects.create(
            name='Kurczak',
            category=self.meat_category
        )
        
        # Tworzenie jednostek miary
        self.gram = MeasurementUnit.objects.create(
            name='Gram',
            symbol='g',
            type='weight',
            base_ratio=1.0
        )
        
        # Tworzenie przepisów
        self.potato_recipe = Recipe.objects.create(
            title='Pieczone ziemniaki',
            description='Prosty przepis na ziemniaki',
            instructions='Instrukcje',
            servings=2,
            preparation_time=30,
            author=self.user
        )
        
        self.carrot_recipe = Recipe.objects.create(
            title='Gotowana marchew',
            description='Prosty przepis na marchew',
            instructions='Instrukcje',
            servings=2,
            preparation_time=15,
            author=self.user
        )
        
        self.chicken_recipe = Recipe.objects.create(
            title='Pieczony kurczak',
            description='Przepis na kurczaka',
            instructions='Instrukcje',
            servings=4,
            preparation_time=60,
            author=self.user
        )
        
        # Dodawanie składników do przepisów
        RecipeIngredient.objects.create(
            recipe=self.potato_recipe,
            ingredient=self.potato,
            amount=500,
            unit=self.gram
        )
        
        RecipeIngredient.objects.create(
            recipe=self.carrot_recipe,
            ingredient=self.carrot,
            amount=300,
            unit=self.gram
        )
        
        RecipeIngredient.objects.create(
            recipe=self.chicken_recipe,
            ingredient=self.chicken,
            amount=1000,
            unit=self.gram
        )
        
        # Dodanie składników do lodówki
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.potato,
            amount=1000,
            unit=self.gram
        )
        
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.carrot,
            amount=100,  # Za mało na przepis
            unit=self.gram
        )
    
    def test_filter_by_available_ingredients(self):
        """Test filtrowania przepisów według dostępności składników"""
        from django.db.models import Q
        
        # Pobierz wszystkie przepisy
        all_recipes = Recipe.objects.filter(Q(author=self.user) | Q(is_public=True)).distinct()
        self.assertEqual(all_recipes.count(), 3)
        
        # Filtruj przepisy dostępne ze składników w lodówce
        available_recipe_ids = []
        for recipe in all_recipes:
            if recipe.can_be_prepared_with_available_ingredients(self.user):
                available_recipe_ids.append(recipe.id)
        
        available_recipes = Recipe.objects.filter(id__in=available_recipe_ids)
        
        # Powinien być tylko jeden dostępny przepis (ziemniaki)
        self.assertEqual(available_recipes.count(), 1)
        self.assertEqual(available_recipes.first().title, 'Pieczone ziemniaki')
    
    def test_update_fridge_affects_availability(self):
        """Test czy aktualizacja zawartości lodówki wpływa na dostępność przepisów"""
        # Początkowo tylko przepis na ziemniaki jest dostępny
        self.assertTrue(self.potato_recipe.can_be_prepared_with_available_ingredients(self.user))
        self.assertFalse(self.carrot_recipe.can_be_prepared_with_available_ingredients(self.user))
        self.assertFalse(self.chicken_recipe.can_be_prepared_with_available_ingredients(self.user))
        
        # Aktualizacja lodówki - dodanie większej ilości marchwi
        FridgeItem.add_to_fridge(
            user=self.user,
            ingredient=self.carrot,
            amount=300,
            unit=self.gram
        )
        
        # Teraz przepisy na ziemniaki i marchew powinny być dostępne
        self.assertTrue(self.potato_recipe.can_be_prepared_with_available_ingredients(self.user))
        self.assertTrue(self.carrot_recipe.can_be_prepared_with_available_ingredients(self.user))
        self.assertFalse(self.chicken_recipe.can_be_prepared_with_available_ingredients(self.user))
