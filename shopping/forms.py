from django import forms
from .models import ShoppingListItem

class ShoppingListItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingListItem
        fields = ['name', 'quantity', 'unit', 'recipe_name']
