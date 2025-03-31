from django.contrib import admin
from .models import (
    Recipe, RecipeIngredient, RecipeCategory, 
    Ingredient, IngredientCategory, MeasurementUnit, UnitConversion,
    RecipeStep, RecipeImage
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
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'default_unit')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    filter_horizontal = ('compatible_units',)
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'description', 'barcode')
        }),
        ('Jednostki miary', {
            'fields': ('default_unit', 'compatible_units', 'density', 'piece_weight')
        })
    )

@admin.register(MeasurementUnit)
class MeasurementUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'type', 'base_ratio')
    list_filter = ('type',)
    search_fields = ('name', 'symbol')
    ordering = ('type', 'name')

class UnitConversionInline(admin.TabularInline):
    model = UnitConversion
    fk_name = 'ingredient'
    extra = 1

@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'from_unit', 'to_unit', 'ratio')
    list_filter = ('from_unit', 'to_unit')
    search_fields = ('ingredient__name',)

@admin.register(RecipeStep)
class RecipeStepAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'step_number', 'description')
    list_filter = ('recipe',)
    search_fields = ('recipe__title', 'description')
    ordering = ('recipe', 'step_number')

@admin.register(RecipeImage)
class RecipeImageAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'image', 'is_main')
    list_filter = ('recipe', 'is_main')
    search_fields = ('recipe__title',)

class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 1
    ordering = ['step_number']

class RecipeImageInline(admin.TabularInline):
    model = RecipeImage
    extra = 1
    fields = ['image', 'description', 'is_main']
