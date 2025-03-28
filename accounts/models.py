from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    fridge_name = models.CharField(max_length=100, default="Moja Lodówka", verbose_name="Nazwa lodówki")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Zdjęcie profilowe")
    bio = models.TextField(blank=True, verbose_name="O sobie")
    favorite_cuisine = models.CharField(max_length=100, blank=True, verbose_name="Ulubiona kuchnia")
    
    class Meta:
        verbose_name = "Profil użytkownika"
        verbose_name_plural = "Profile użytkowników"

    def __str__(self):
        return self.user.username
    
    @property
    def recipe_count(self):
        """Zwraca liczbę przepisów utworzonych przez użytkownika"""
        return self.user.recipe_set.count()
    
    @property
    def fridge_items_count(self):
        """Zwraca liczbę produktów w lodówce użytkownika"""
        return self.user.fridge_items.count()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatycznie tworzy profil dla nowego użytkownika"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Zapisuje profil użytkownika przy zapisie użytkownika"""
    instance.profile.save()
