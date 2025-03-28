from django.contrib import admin
from .models import (
    Recipe, RecipeIngredient, RecipeCategory, 
    Ingredient, IngredientCategory, MeasurementUnit, UnitConversion
)

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 3

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'get_categories', 'servings', 'preparation_time', 'is_vegetarian', 'is_vegan', 'created_at')
    list_filter = ('categories', 'author', 'created_at')
    search_fields = ('title', 'description', 'instructions')
    inlines = [RecipeIngredientInline]
    
    def get_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()])
    get_categories.short_description = 'Kategorie'

@admin.register(RecipeCategory)
class RecipeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(IngredientCategory)
class IngredientCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_vegetarian', 'is_vegan')
    list_filter = ('is_vegetarian', 'is_vegan')
    search_fields = ('name',)

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_vegetarian', 'is_vegan')
    list_filter = ('category', 'category__is_vegetarian', 'category__is_vegan')
    search_fields = ('name', 'description')

@admin.register(MeasurementUnit)
class MeasurementUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'is_base')
    list_filter = ('is_base',)
    search_fields = ('name', 'symbol')

@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ('from_unit', 'to_unit', 'ratio')
    list_filter = ('from_unit', 'to_unit')
    search_fields = ('from_unit__name', 'to_unit__name')
