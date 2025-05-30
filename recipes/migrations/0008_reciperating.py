# Generated by Django 5.2 on 2025-04-14 22:57

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0007_alter_conversiontable_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecipeRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, '1 - Bardzo słabo'), (2, '2 - Słabo'), (3, '3 - Przeciętnie'), (4, '4 - Dobrze'), (5, '5 - Bardzo dobrze')], verbose_name='Ocena')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data dodania')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='Komentarz do oceny')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='recipes.recipe', verbose_name='Przepis')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_ratings', to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
            ],
            options={
                'verbose_name': 'Ocena przepisu',
                'verbose_name_plural': 'Oceny przepisów',
                'unique_together': {('user', 'recipe')},
            },
        ),
    ]
