from django import forms
from .models import FridgeItem

class FridgeItemForm(forms.ModelForm):
    class Meta:
        model = FridgeItem
        fields = ['name', 'quantity', 'unit', 'expiry_date']
