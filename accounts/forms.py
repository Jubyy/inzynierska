from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
        help_texts = {
            'username': 'Wybierz unikalną nazwę użytkownika (bez spacji i znaków specjalnych).',
        }
        error_messages = {
            'username': {
                'unique': 'Użytkownik o tej nazwie już istnieje.',
                'invalid': 'Nazwa użytkownika może zawierać tylko litery, cyfry i znaki @/./+/-/_.',
            },
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dostosowanie widgetów dla pól z formularza bazowego
        self.fields['password1'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Hasło'})
        self.fields['password2'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Powtórz hasło'})
        
        # Dostosowanie etykiet
        self.fields['password1'].label = 'Hasło'
        self.fields['password2'].label = 'Powtórz hasło'
        
        # Przetłumaczenie komunikatów o błędach hasła
        self.fields['password1'].help_text = '<ul><li>Twoje hasło nie może być zbyt podobne do twoich innych danych osobowych.</li><li>Twoje hasło musi zawierać co najmniej 8 znaków.</li><li>Twoje hasło nie może być często używanym hasłem.</li><li>Twoje hasło nie może składać się tylko z cyfr.</li></ul>'
        
        self.error_messages['password_mismatch'] = 'Podane hasła nie są identyczne.'
        
        # Zastąpienie domyślnych komunikatów błędów
        self.fields['password2'].error_messages = {
            'required': 'To pole jest wymagane.',
        }
        self.fields['password1'].error_messages = {
            'required': 'To pole jest wymagane.',
        }
        
    def clean_email(self):
        """Sprawdza, czy email jest unikalny"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Użytkownik z tym adresem email już istnieje.")
        return email

class CustomAuthenticationForm(AuthenticationForm):
    """Niestandardowy formularz logowania sprawdzający aktywację konta"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nazwa użytkownika'})
        self.fields['password'].widget = forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Hasło'})
        
        # Polskie komunikaty błędów
        self.error_messages = {
            'invalid_login': 'Wprowadź poprawną nazwę użytkownika i hasło. Pamiętaj, że oba pola mogą być wrażliwe na wielkość liter.',
            'inactive': 'To konto jest nieaktywne.',
        }
    
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(
                "To konto nie zostało jeszcze aktywowane. "
                "Sprawdź swoją skrzynkę email, aby odnaleźć link aktywacyjny, "
                "lub kliknij 'Zapomniałem hasła', aby otrzymać nowy link."
            )
        super().confirm_login_allowed(user)

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
        
        # Polskie komunikaty błędów
        self.error_messages = {
            'password_mismatch': 'Podane hasła nie są identyczne.',
            'password_incorrect': 'Twoje stare hasło zostało wprowadzone niepoprawnie. Spróbuj ponownie.',
        }
        
        # Przetłumaczenie pomocy do hasła
        self.fields['new_password1'].help_text = '<ul><li>Twoje hasło nie może być zbyt podobne do twoich innych danych osobowych.</li><li>Twoje hasło musi zawierać co najmniej 8 znaków.</li><li>Twoje hasło nie może być często używanym hasłem.</li><li>Twoje hasło nie może składać się tylko z cyfr.</li></ul>' 