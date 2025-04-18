# Generated by Django 5.1.6 on 2025-03-30 20:42

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IngredientCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nazwa kategorii')),
                ('is_vegetarian', models.BooleanField(default=True, verbose_name='Wegetariański')),
                ('is_vegan', models.BooleanField(default=False, verbose_name='Wegański')),
            ],
            options={
                'verbose_name': 'Kategoria składnika',
                'verbose_name_plural': 'Kategorie składników',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='MeasurementUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Nazwa')),
                ('symbol', models.CharField(max_length=10, verbose_name='Symbol')),
                ('type', models.CharField(choices=[('weight', 'Waga'), ('volume', 'Objętość'), ('piece', 'Sztuki'), ('custom', 'Niestandardowa')], default='weight', max_length=20, verbose_name='Typ jednostki')),
                ('base_ratio', models.DecimalField(decimal_places=4, default=Decimal('1.0000'), help_text='Współczynnik przeliczeniowy na jednostkę bazową (g dla wagi, ml dla objętości)', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.0001'))], verbose_name='Współczynnik przeliczeniowy')),
            ],
            options={
                'verbose_name': 'Jednostka miary',
                'verbose_name_plural': 'Jednostki miary',
                'ordering': ['type', 'name'],
            },
        ),
        migrations.CreateModel(
            name='RecipeCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nazwa kategorii')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Opis')),
            ],
            options={
                'verbose_name': 'Kategoria przepisu',
                'verbose_name_plural': 'Kategorie przepisów',
            },
        ),
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nazwa składnika')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Opis')),
                ('barcode', models.CharField(blank=True, max_length=30, null=True, unique=True, verbose_name='Kod kreskowy')),
                ('density', models.DecimalField(blank=True, decimal_places=3, help_text='Gęstość w g/ml (dla konwersji między wagą a objętością)', max_digits=8, null=True, verbose_name='Gęstość [g/ml]')),
                ('piece_weight', models.DecimalField(blank=True, decimal_places=2, help_text='Waga jednej sztuki w gramach', max_digits=8, null=True, verbose_name='Waga sztuki [g]')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredients', to='recipes.ingredientcategory', verbose_name='Kategoria')),
                ('compatible_units', models.ManyToManyField(blank=True, related_name='compatible_ingredients', to='recipes.measurementunit', verbose_name='Kompatybilne jednostki')),
                ('default_unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='default_for_ingredients', to='recipes.measurementunit', verbose_name='Domyślna jednostka')),
            ],
            options={
                'verbose_name': 'Składnik',
                'verbose_name_plural': 'Składniki',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Tytuł')),
                ('description', models.TextField(verbose_name='Opis')),
                ('instructions', models.TextField(verbose_name='Instrukcje przygotowania')),
                ('servings', models.PositiveIntegerField(default=4, verbose_name='Liczba porcji')),
                ('preparation_time', models.PositiveIntegerField(help_text='Czas przygotowania w minutach', verbose_name='Czas przygotowania')),
                ('difficulty', models.CharField(choices=[('easy', 'Łatwy'), ('medium', 'Średni'), ('hard', 'Trudny')], default='medium', max_length=10, verbose_name='Poziom trudności')),
                ('image', models.ImageField(blank=True, null=True, upload_to='recipes/', verbose_name='Zdjęcie')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')),
                ('is_public', models.BooleanField(default=True, verbose_name='Publiczny')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Autor')),
                ('categories', models.ManyToManyField(related_name='recipes', to='recipes.recipecategory', verbose_name='Kategorie')),
            ],
            options={
                'verbose_name': 'Przepis',
                'verbose_name_plural': 'Przepisy',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='Treść komentarza')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data dodania')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='recipes.comment', verbose_name='Komentarz nadrzędny')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_comments', to=settings.AUTH_USER_MODEL, verbose_name='Autor')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='recipes.recipe', verbose_name='Przepis')),
            ],
            options={
                'verbose_name': 'Komentarz',
                'verbose_name_plural': 'Komentarze',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RecipeImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='recipes/', verbose_name='Zdjęcie')),
                ('description', models.CharField(blank=True, max_length=200, null=True, verbose_name='Opis zdjęcia')),
                ('is_main', models.BooleanField(default=False, verbose_name='Zdjęcie główne')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='Data dodania')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='recipes.recipe', verbose_name='Przepis')),
            ],
            options={
                'verbose_name': 'Zdjęcie przepisu',
                'verbose_name_plural': 'Zdjęcia przepisu',
                'ordering': ['-is_main', '-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='MealPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Data')),
                ('meal_type', models.CharField(choices=[('breakfast', 'Śniadanie'), ('lunch', 'Drugie śniadanie'), ('dinner', 'Obiad'), ('snack', 'Przekąska'), ('supper', 'Kolacja')], max_length=20, verbose_name='Rodzaj posiłku')),
                ('servings', models.PositiveIntegerField(default=1, verbose_name='Liczba porcji')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='Notatki')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')),
                ('completed', models.BooleanField(default=False, verbose_name='Zrealizowano')),
                ('custom_name', models.CharField(blank=True, max_length=200, null=True, verbose_name='Własna nazwa posiłku')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meal_plans', to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
                ('recipe', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='meal_plans', to='recipes.recipe', verbose_name='Przepis')),
            ],
            options={
                'verbose_name': 'Plan posiłku',
                'verbose_name_plural': 'Plany posiłków',
                'ordering': ['date', 'meal_type'],
                'unique_together': {('user', 'date', 'meal_type', 'recipe')},
            },
        ),
        migrations.CreateModel(
            name='FavoriteRecipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='Data dodania')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_recipes', to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='recipes.recipe', verbose_name='Przepis')),
            ],
            options={
                'verbose_name': 'Ulubiony przepis',
                'verbose_name_plural': 'Ulubione przepisy',
                'unique_together': {('user', 'recipe')},
            },
        ),
        migrations.CreateModel(
            name='RecipeIngredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(verbose_name='Ilość')),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.ingredient', verbose_name='Składnik')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredients', to='recipes.recipe', verbose_name='Przepis')),
                ('unit', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='recipes.measurementunit', verbose_name='Jednostka')),
            ],
            options={
                'verbose_name': 'Składnik przepisu',
                'verbose_name_plural': 'Składniki przepisu',
                'unique_together': {('recipe', 'ingredient')},
            },
        ),
        migrations.CreateModel(
            name='RecipeLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data dodania')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='recipes.recipe', verbose_name='Przepis')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipe_likes', to=settings.AUTH_USER_MODEL, verbose_name='Użytkownik')),
            ],
            options={
                'verbose_name': 'Polubienie przepisu',
                'verbose_name_plural': 'Polubienia przepisów',
                'unique_together': {('user', 'recipe')},
            },
        ),
        migrations.CreateModel(
            name='RecipeStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_number', models.PositiveIntegerField(verbose_name='Numer kroku')),
                ('description', models.TextField(verbose_name='Opis kroku')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='recipes.recipe', verbose_name='Przepis')),
            ],
            options={
                'verbose_name': 'Krok przepisu',
                'verbose_name_plural': 'Kroki przepisu',
                'ordering': ['recipe', 'step_number'],
                'unique_together': {('recipe', 'step_number')},
            },
        ),
        migrations.CreateModel(
            name='UnitConversion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ratio', models.DecimalField(decimal_places=4, max_digits=10)),
                ('from_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversions_from', to='recipes.measurementunit')),
                ('ingredient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='recipes.ingredient')),
                ('to_unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversions_to', to='recipes.measurementunit')),
            ],
            options={
                'verbose_name': 'Konwersja jednostek',
                'verbose_name_plural': 'Konwersje jednostek',
                'unique_together': {('from_unit', 'to_unit', 'ingredient')},
            },
        ),
    ]
