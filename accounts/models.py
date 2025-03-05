from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fridge_name = models.CharField(max_length=100, default="Moja Lodówka")

    def __str__(self):
        return self.user.username
