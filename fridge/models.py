from django.db import models
from django.contrib.auth.models import User

class FridgeItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20, choices=[
        ('szt', 'sztuk'),
        ('g', 'gramy'),
        ('ml', 'mililitry'),
        ('szklanka', 'szklanki')
    ])
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} - {self.quantity} {self.unit}'


