from django import forms
from .models import Recipe, RecipeIngredient, PreparationStep

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'description', 'portions', 'category', 'image']


class RecipeIngredientForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredient
        fields = ['name', 'quantity', 'unit']

class PreparationStepForm(forms.ModelForm):
    class Meta:
        model = PreparationStep
        fields = ['description']
