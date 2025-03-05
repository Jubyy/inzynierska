from django.db import models
from django.contrib.auth.models import User

class ShoppingListItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20)
    recipe_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.name} ({self.quantity} {self.unit}) - do przepisu: {self.recipe_name}'
