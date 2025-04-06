from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

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

class RecipeHistory(models.Model):
    """Model przechowujący historię przygotowanych przepisów przez użytkownika"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipe_history', verbose_name="Użytkownik")
    recipe = models.ForeignKey('recipes.Recipe', on_delete=models.SET_NULL, null=True, related_name='preparation_history', verbose_name="Przepis")
    recipe_name = models.CharField(max_length=200, verbose_name="Nazwa przepisu")  # Zapisujemy nazwę w przypadku usunięcia przepisu
    prepared_at = models.DateTimeField(default=timezone.now, verbose_name="Data przygotowania")
    servings = models.PositiveIntegerField(default=1, verbose_name="Liczba porcji")
    notes = models.TextField(blank=True, verbose_name="Notatki")
    
    class Meta:
        verbose_name = "Historia przepisów"
        verbose_name_plural = "Historia przepisów"
        ordering = ['-prepared_at']
        
    def __str__(self):
        return f"{self.recipe_name} - {self.prepared_at.strftime('%d.%m.%Y')}"
    
    @classmethod
    def add_to_history(cls, user, recipe, servings=None, notes=''):
        """Dodaj przygotowany przepis do historii użytkownika"""
        if servings is None:
            servings = recipe.servings
        
        return cls.objects.create(
            user=user,
            recipe=recipe,
            recipe_name=recipe.title,
            servings=servings,
            notes=notes
        )

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatycznie tworzy profil dla nowego użytkownika"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Zapisuje profil użytkownika przy zapisie użytkownika"""
    instance.profile.save()
