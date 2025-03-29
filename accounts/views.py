from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse

from recipes.models import Recipe
from fridge.models import FridgeItem
from shopping.models import ShoppingList

from .models import UserProfile
from .forms import UserProfileForm, CustomUserCreationForm, CustomPasswordChangeForm

def register(request):
    """Rejestracja nowego użytkownika"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Konto zostało utworzone pomyślnie!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Wystąpił błąd podczas rejestracji. Popraw błędy i spróbuj ponownie.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

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
    
    context = {
        'user_recipes': user_recipes,
        'fridge_items': fridge_items,
        'shopping_lists': shopping_lists,
        'expired_count': len(expired_items),
        'available_recipes': available_recipes,
        'recipe_count': Recipe.objects.filter(author=request.user).count(),
        'fridge_item_count': FridgeItem.objects.filter(user=request.user).count(),
        'shopping_list_count': ShoppingList.objects.filter(user=request.user).count()
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
