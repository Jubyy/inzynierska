from django.contrib import admin
from .models import ShoppingList, ShoppingItem

class ShoppingItemInline(admin.TabularInline):
    model = ShoppingItem
    extra = 1

@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'item_count', 'created_at', 'modified_at', 'is_completed')
    list_filter = ('user', 'is_completed', 'created_at')
    search_fields = ('name', 'user__username')
    date_hierarchy = 'created_at'
    inlines = [ShoppingItemInline]
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Liczba pozycji'

@admin.register(ShoppingItem)
class ShoppingItemAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'amount', 'unit', 'shopping_list', 'is_purchased', 'purchase_date')
    list_filter = ('is_purchased', 'shopping_list', 'ingredient', 'purchase_date')
    search_fields = ('ingredient__name', 'shopping_list__name', 'shopping_list__user__username')
    date_hierarchy = 'purchase_date'
