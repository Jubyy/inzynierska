# Generated by Django 5.2 on 2025-04-06 20:01

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('recipes', '0004_ingredient_unit_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecipeHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipe_name', models.CharField(max_length=200, verbose_name='Nazwa przepisu')),
                ('prepared_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data przygotowania')),
                ('servings', models.PositiveIntegerField(default=1, verbose_name='Liczba porcji')),
                ('notes', models.TextField(blank=True, verbose_name='Notatki')),
                ('recipe', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='preparation_history', to='recipes.recipe', verbose_name='Przepis')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_history', to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
            ],
            options={
                'verbose_name': 'Historia przepisów',
                'verbose_name_plural': 'Historia przepisów',
                'ordering': ['-prepared_at'],
            },
        ),
    ]
