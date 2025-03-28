from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    """Rozszerzony formularz rejestracji użytkownika"""
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Adres email'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Imię'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwisko'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa użytkownika'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dostosowanie widgetów dla pól z formularza bazowego
        self.fields['password1'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Hasło'})
        self.fields['password2'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Powtórz hasło'})
        
        # Dostosowanie etykiet
        self.fields['password1'].label = 'Hasło'
        self.fields['password2'].label = 'Powtórz hasło'
        
class UserProfileForm(forms.ModelForm):
    """Formularz do edycji profilu użytkownika"""
    class Meta:
        model = UserProfile
        fields = ('avatar', 'bio', 'favorite_cuisine', 'fridge_name')
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Napisz coś o sobie...'}),
            'favorite_cuisine': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Twoja ulubiona kuchnia'}),
            'fridge_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa Twojej lodówki'})
        }
        labels = {
            'avatar': 'Zdjęcie profilowe',
            'bio': 'O mnie',
            'favorite_cuisine': 'Ulubiona kuchnia',
            'fridge_name': 'Nazwa lodówki'
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    """Rozszerzony formularz zmiany hasła"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dostosowanie widgetów
        self.fields['old_password'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Aktualne hasło'})
        self.fields['new_password1'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nowe hasło'})
        self.fields['new_password2'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Powtórz nowe hasło'})
        
        # Dostosowanie etykiet
        self.fields['old_password'].label = 'Aktualne hasło'
        self.fields['new_password1'].label = 'Nowe hasło'
        self.fields['new_password2'].label = 'Powtórz nowe hasło' 