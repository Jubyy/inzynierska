from django.contrib import admin
from .models import (
    Recipe, RecipeIngredient, RecipeCategory, 
    Ingredient, IngredientCategory, MeasurementUnit, UnitConversion,
    RecipeStep, RecipeImage, FavoriteRecipe, RecipeLike,
    Comment, IngredientUnit, IngredientConversion,
    ConversionTable, ConversionTableEntry, UserIngredient, RecipeRating
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

@admin.register(MeasurementUnit)
class MeasurementUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'type', 'base_ratio', 'is_common')
    list_filter = ('type', 'is_common')
    search_fields = ('name', 'symbol')
    ordering = ('type', 'name')

class UnitConversionInline(admin.TabularInline):
    model = UnitConversion
    fk_name = 'ingredient'
    extra = 1

@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ('from_unit', 'to_unit', 'ratio', 'ingredient')
    list_filter = ('from_unit', 'to_unit')
    search_fields = ('from_unit__name', 'to_unit__name', 'ingredient__name')
    autocomplete_fields = ('from_unit', 'to_unit', 'ingredient')

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

class IngredientUnitInline(admin.TabularInline):
    model = IngredientUnit
    extra = 1

class IngredientConversionInline(admin.TabularInline):
    model = IngredientConversion
    fk_name = 'ingredient'
    extra = 1
    fields = ['from_unit', 'to_unit', 'ratio', 'is_exact']

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'default_unit', 'is_vegetarian', 'is_vegan')
    list_filter = ('category', 'unit_type')
    search_fields = ('name', 'category__name')
    autocomplete_fields = ('category', 'default_unit', 'compatible_units')
    inlines = [IngredientUnitInline, IngredientConversionInline]

@admin.register(IngredientConversion)
class IngredientConversionAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'from_unit', 'to_unit', 'ratio', 'is_exact')
    search_fields = ('ingredient__name', 'from_unit__name', 'to_unit__name')
    list_filter = ('is_exact', 'from_unit', 'to_unit')
    autocomplete_fields = ('ingredient', 'from_unit', 'to_unit')

@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'added_at')
    search_fields = ('user__username', 'recipe__title')
    list_filter = ('added_at',)
    autocomplete_fields = ('user', 'recipe')

@admin.register(RecipeLike)
class RecipeLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'created_at')
    search_fields = ('user__username', 'recipe__title')
    list_filter = ('created_at',)
    autocomplete_fields = ('user', 'recipe')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'created_at', 'is_reply')
    search_fields = ('user__username', 'recipe__title', 'content')
    list_filter = ('created_at',)
    autocomplete_fields = ('user', 'recipe', 'parent')

@admin.register(IngredientUnit)
class IngredientUnitAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'unit', 'is_default')
    search_fields = ('ingredient__name', 'unit__name')
    list_filter = ('is_default', 'unit')
    autocomplete_fields = ('ingredient', 'unit')

class ConversionTableEntryInline(admin.TabularInline):
    model = ConversionTableEntry
    extra = 1
    fields = ['from_unit', 'to_unit', 'ratio', 'is_exact', 'notes']
    autocomplete_fields = ['from_unit', 'to_unit']

@admin.register(ConversionTable)
class ConversionTableAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_for_liquids', 'is_approved', 'created_by', 'created_at']
    search_fields = ['name', 'category__name']
    list_filter = ['category', 'is_for_liquids', 'is_approved', 'created_at']
    inlines = [ConversionTableEntryInline]
    autocomplete_fields = ['category', 'created_by']
    actions = ['mark_as_approved', 'mark_as_not_approved']
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'Zatwierdzono {updated} tablic konwersji')
    mark_as_approved.short_description = "Oznacz wybrane tablice jako zatwierdzone"
    
    def mark_as_not_approved(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'Cofnięto zatwierdzenie dla {updated} tablic konwersji')
    mark_as_not_approved.short_description = "Oznacz wybrane tablice jako niezatwierdzone"

@admin.register(ConversionTableEntry)
class ConversionTableEntryAdmin(admin.ModelAdmin):
    list_display = ['table', 'from_unit', 'to_unit', 'ratio', 'is_exact']
    search_fields = ['table__name', 'from_unit__name', 'to_unit__name']
    list_filter = ['is_exact', 'table']
    autocomplete_fields = ['table', 'from_unit', 'to_unit']

@admin.register(UserIngredient)
class UserIngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'user', 'status', 'submitted_at']
    list_filter = ['status', 'category', 'unit_type', 'submitted_at']
    search_fields = ['name', 'user__username', 'admin_notes']
    readonly_fields = ['submitted_at']
    fieldsets = (
        ('Informacje podstawowe', {
            'fields': ('name', 'category', 'description')
        }),
        ('Jednostki i konwersje', {
            'fields': ('default_unit', 'conversion_table', 'unit_type', 'density', 'piece_weight')
        }),
        ('Informacje o zgłoszeniu', {
            'fields': ('user', 'submitted_at', 'status', 'admin_notes')
        }),
    )
    actions = ['approve_ingredients', 'reject_ingredients']
    
    def approve_ingredients(self, request, queryset):
        for user_ingredient in queryset.filter(status='pending'):
            try:
                ingredient = user_ingredient.approve(admin_user=request.user)
                self.message_user(request, f'Zatwierdzono składnik: {ingredient.name}')
            except Exception as e:
                self.message_user(request, f'Błąd podczas zatwierdzania {user_ingredient.name}: {str(e)}', level='error')
    approve_ingredients.short_description = "Zatwierdź wybrane składniki"
    
    def reject_ingredients(self, request, queryset):
        for user_ingredient in queryset.filter(status='pending'):
            try:
                user_ingredient.reject(admin_user=request.user)
                self.message_user(request, f'Odrzucono składnik: {user_ingredient.name}')
            except Exception as e:
                self.message_user(request, f'Błąd podczas odrzucania {user_ingredient.name}: {str(e)}', level='error')
    reject_ingredients.short_description = "Odrzuć wybrane składniki"

@admin.register(RecipeRating)
class RecipeRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'recipe__title', 'comment')
    autocomplete_fields = ('user', 'recipe')
