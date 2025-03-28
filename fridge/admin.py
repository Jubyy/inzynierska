from django.contrib import admin
from .models import FridgeItem

@admin.register(FridgeItem)
class FridgeItemAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'amount', 'unit', 'user', 'expiry_date', 'purchase_date', 'is_expired')
    list_filter = ('user', 'ingredient', 'expiry_date', 'purchase_date')
    search_fields = ('ingredient__name', 'user__username')
    date_hierarchy = 'purchase_date'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Przeterminowane'
