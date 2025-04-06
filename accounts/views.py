from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.db.models.query_utils import Q
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Count

from recipes.models import Recipe
from fridge.models import FridgeItem
from shopping.models import ShoppingList

from .models import UserProfile
from .forms import UserProfileForm, CustomUserCreationForm, CustomPasswordChangeForm

# Funkcja pomocnicza do wysyłania emaili
def send_email(request, user, subject_template, email_template):
    current_site = get_current_site(request)
    subject = render_to_string(subject_template)
    body = render_to_string(email_template, {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http',
    })
    email = EmailMessage(subject, body, to=[user.email])
    email.content_subtype = 'html'  # Używamy HTML w emailach
    return email.send()

def register(request):
    """Rejestracja nowego użytkownika z weryfikacją email"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Tworzymy użytkownika, ale nie zapisujemy go jeszcze (commit=False)
            user = form.save(commit=False)
            user.is_active = False  # Deaktywuj użytkownika do momentu weryfikacji email
            user.save()
            
            # Wyślij email z linkiem aktywacyjnym
            try:
                send_email(
                    request, 
                    user, 
                    'accounts/email/activation_subject.txt',
                    'accounts/email/activation_email.html'
                )
                messages.success(
                    request, 
                    'Twoje konto zostało utworzone! Na podany adres email wysłaliśmy link aktywacyjny. '
                    'Sprawdź swoją skrzynkę (również folder SPAM) i kliknij w link, aby aktywować konto.'
                )
                return redirect('accounts:activation_sent')
            except Exception as e:
                messages.error(
                    request, 
                    f'Wystąpił problem podczas wysyłania emaila aktywacyjnego: {str(e)}. '
                    'Skontaktuj się z administratorem.'
                )
                # W przypadku błędu, usuwamy utworzonego użytkownika
                user.delete()
        else:
            messages.error(request, 'Wystąpił błąd podczas rejestracji. Popraw błędy i spróbuj ponownie.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def activate_account(request, uidb64, token):
    """Aktywacja konta użytkownika poprzez link z emaila"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Sprawdź czy użytkownik istnieje i token jest prawidłowy
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'Twoje konto zostało aktywowane! Możesz teraz korzystać z serwisu.')
        return redirect('accounts:dashboard')
    else:
        messages.error(request, 'Link aktywacyjny jest nieprawidłowy lub wygasł.')
        return redirect('login')

def activation_sent(request):
    """Strona potwierdzająca wysłanie linku aktywacyjnego"""
    return render(request, 'accounts/activation_sent.html')

@login_required
def dashboard(request):
    """Główny panel użytkownika"""
    # Pobierz ostatnie przepisy użytkownika
    user_recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')[:5]
    
    # Pobierz produkty z lodówki
    fridge_items = FridgeItem.objects.filter(user=request.user).order_by('ingredient__name')[:10]
    
    # Pobierz aktywne listy zakupów
    shopping_lists = ShoppingList.objects.filter(user=request.user, is_completed=False).order_by('-created_at')[:3]
    
    # Sprawdź przeterminowane produkty
    expired_items = [item for item in FridgeItem.objects.filter(user=request.user) if item.is_expired]
    
    # Pobierz przepisy, które można przygotować z dostępnych składników
    available_recipes = []
    recipes = Recipe.objects.all().order_by('-created_at')[:20]  # Ogranicz do 20 najnowszych przepisów
    
    for recipe in recipes:
        if recipe.can_be_prepared_with_available_ingredients(request.user):
            available_recipes.append(recipe)
            if len(available_recipes) >= 5:  # Ogranicz do 5 przepisów
                break
    
    # Pobierz top 3 najlepsze przepisy (z największą liczbą polubień)
    top_recipes = Recipe.objects.annotate(
        likes_total=Count('likes')
    ).order_by('-likes_total', '-created_at')[:3]
    
    # Pobierz ranking użytkowników (top 5) dodających najwięcej przepisów
    top_users = User.objects.annotate(
        recipes_count=Count('recipe')
    ).order_by('-recipes_count')[:5]
    
    context = {
        'user_recipes': user_recipes,
        'fridge_items': fridge_items,
        'shopping_lists': shopping_lists,
        'expired_count': len(expired_items),
        'available_recipes': available_recipes,
        'recipe_count': Recipe.objects.filter(author=request.user).count(),
        'fridge_item_count': FridgeItem.objects.filter(user=request.user).count(),
        'shopping_list_count': ShoppingList.objects.filter(user=request.user).count(),
        'top_recipes': top_recipes,
        'top_users': top_users
    }
    
    return render(request, 'accounts/dashboard.html', context)

def custom_logout(request):
    """Wylogowywanie użytkownika"""
    logout(request)
    messages.success(request, 'Wylogowano pomyślnie.')
    return redirect('login')

@login_required
def profile(request):
    """Widok profilu użytkownika"""
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Twój profil został zaktualizowany!')
            return redirect('profile')
    else:
        user_form = CustomUserCreationForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)
    
    # Pobierz przepisy użytkownika
    user_recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')[:5]
    
    # Pobierz statystyki
    recipes_count = Recipe.objects.filter(author=request.user).count()
    fridge_count = FridgeItem.objects.filter(user=request.user).count()
    shopping_lists_count = ShoppingList.objects.filter(user=request.user).count()
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'recipes': user_recipes,
        'recipes_count': recipes_count,
        'fridge_count': fridge_count,
        'shopping_lists_count': shopping_lists_count
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password(request):
    """Zmiana hasła użytkownika"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Zachowaj sesję użytkownika po zmianie hasła
            update_session_auth_hash(request, user)
            messages.success(request, 'Hasło zostało zmienione pomyślnie!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Popraw błędy w formularzu.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def user_recipes(request):
    """Lista przepisów użytkownika"""
    recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'accounts/user_recipes.html', {'recipes': recipes})

class UserProfileDetailView(LoginRequiredMixin, DetailView):
    """Szczegółowy widok profilu użytkownika"""
    model = UserProfile
    template_name = 'accounts/user_detail.html'
    context_object_name = 'profile'
    
    def get_object(self):
        username = self.kwargs.get('username')
        return UserProfile.objects.get(user__username=username)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.get_object().user
        
        # Dodaj publiczne przepisy użytkownika
        context['recipes'] = Recipe.objects.filter(author=user).order_by('-created_at')
        
        return context

class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Edycja profilu użytkownika"""
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user.profile
    
    def form_valid(self, form):
        messages.success(self.request, 'Profil został zaktualizowany!')
        return super().form_valid(form)

@login_required
def delete_account(request):
    """Usuwanie konta użytkownika"""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = request.user
        
        # Sprawdź, czy hasło jest poprawne
        if authenticate(username=user.username, password=password):
            # Zapisz informacje o użytkowniku, aby użyć w komunikacie
            username = user.username
            
            # Wyloguj użytkownika
            logout(request)
            
            # Usuń konto
            user.delete()
            
            messages.success(request, f'Konto {username} zostało usunięte.')
            return redirect('home')  # lub inna strona główna
        else:
            messages.error(request, 'Nieprawidłowe hasło. Spróbuj ponownie.')
    
    return render(request, 'accounts/delete_account.html')
