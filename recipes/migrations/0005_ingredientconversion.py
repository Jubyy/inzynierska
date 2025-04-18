# Generated by Django 5.2 on 2025-04-10 21:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0004_ingredient_unit_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='IngredientConversion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ratio', models.DecimalField(decimal_places=4, max_digits=10, verbose_name='Współczynnik konwersji')),
                ('description', models.CharField(blank=True, max_length=200, verbose_name='Dodatkowy opis')),
                ('is_exact', models.BooleanField(default=True, verbose_name='Dokładna konwersja')),
                ('from_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='from_conversions', to='recipes.measurementunit', verbose_name='Z jednostki')),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversions', to='recipes.ingredient', verbose_name='Składnik')),
                ('to_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='to_conversions', to='recipes.measurementunit', verbose_name='Na jednostkę')),
            ],
            options={
                'verbose_name': 'Konwersja składnika',
                'verbose_name_plural': 'Konwersje składników',
                'ordering': ['ingredient__name', 'from_unit__name', 'to_unit__name'],
                'unique_together': {('ingredient', 'from_unit', 'to_unit')},
            },
        ),
    ]
