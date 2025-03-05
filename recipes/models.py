from django.db import models
from django.contrib.auth.models import User

class Recipe(models.Model):
    CATEGORY_CHOICES = [
        ('obiad', 'Obiad'),
        ('sniadanie', 'Śniadanie'),
        ('kolacja', 'Kolacja'),
        ('deser', 'Deser'),
        ('przekaska', 'Przekąska')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    portions = models.IntegerField(default=1)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    image = models.ImageField(upload_to='recipe_images/', null=True, blank=True)
    
    def is_vegetarian(self):
        return not self.ingredients.filter(category='meat').exists()

    def is_vegan(self):
        return not self.ingredients.filter(category__in=['meat', 'animal']).exists()

    
    def __str__(self):
        return self.name

class RecipeIngredient(models.Model):
    INGREDIENT_CATEGORIES = [
        ('meat', 'Mięsny'),
        ('animal', 'Pochodzenia zwierzęcego'),
        ('plant', 'Roślinny'),
    ]

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=100)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20, choices=[
        ('szt', 'sztuk'),
        ('g', 'gramy'),
        ('ml', 'mililitry'),
        ('szklanka', 'szklanki')
    ])
    category = models.CharField(max_length=10, choices=INGREDIENT_CATEGORIES, default='plant')

    def __str__(self):
        return f'{self.name} - {self.quantity} {self.unit}'



class PreparationStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='steps')
    order = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return f'Krok {self.order}: {self.description[:30]}...'
