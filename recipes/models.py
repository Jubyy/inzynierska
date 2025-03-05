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

    def __str__(self):
        return self.name

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    name = models.CharField(max_length=100)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20, choices=[
        ('szt', 'sztuk'),
        ('g', 'gramy'),
        ('ml', 'mililitry'),
        ('szklanka', 'szklanki')
    ])

    def __str__(self):
        return f'{self.name} - {self.quantity} {self.unit}'
