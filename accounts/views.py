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
from django.db.models import Count, Avg
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST

from recipes.models import Recipe, RecipeLike
from fridge.models import FridgeItem
from shopping.models import ShoppingList

from .models import UserProfile, RecipeHistory, UserFollowing
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
def profile_view(request):
    """Wyświetla profil użytkownika"""
    # Pobierz ulubione przepisy użytkownika
    favorite_recipes = Recipe.objects.filter(favoriterecipe__user=request.user)[:5]
    
    # Pobierz ostatnio dodane przepisy użytkownika
    recent_recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')[:5]
    
    # Pobierz historię przygotowania przepisów
    recipe_history = RecipeHistory.objects.filter(user=request.user)[:5]
    
    # Pobierz liczbę obserwowanych i obserwujących
    following_count = UserFollowing.objects.filter(user=request.user).count()
    followers_count = UserFollowing.objects.filter(followed_user=request.user).count()
    
    context = {
        'user': request.user,
        'favorite_recipes': favorite_recipes,
        'recent_recipes': recent_recipes,
        'recipe_history': recipe_history,
        'following_count': following_count,
        'followers_count': followers_count,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_edit(request):
    """Widok do edycji profilu użytkownika"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Twój profil został zaktualizowany.')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user.profile)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})

@login_required
def user_profile_view(request, username):
    """Wyświetla profil innego użytkownika"""
    user = get_object_or_404(User, username=username)
    
    # Sprawdź, czy zalogowany użytkownik obserwuje tego użytkownika
    is_following = UserFollowing.objects.filter(
        user=request.user, 
        followed_user=user
    ).exists() if request.user.is_authenticated else False
    
    # Pobierz publiczne przepisy użytkownika
    recipes = Recipe.objects.filter(author=user, is_public=True)
    
    # Pobierz liczbę obserwowanych i obserwujących
    following_count = UserFollowing.objects.filter(user=user).count()
    followers_count = UserFollowing.objects.filter(followed_user=user).count()
    
    context = {
        'profile_user': user,
        'recipes': recipes,
        'is_following': is_following,
        'following_count': following_count,
        'followers_count': followers_count,
    }
    
    return render(request, 'accounts/user_profile.html', context)

@login_required
def toggle_follow(request, username):
    """Obserwuj/przestań obserwować użytkownika"""
    user_to_follow = get_object_or_404(User, username=username)
    
    # Nie można obserwować samego siebie
    if request.user == user_to_follow:
        messages.error(request, 'Nie możesz obserwować samego siebie.')
        return redirect('accounts:user_profile', username=username)
    
    # Sprawdź, czy już obserwujesz tego użytkownika
    following_obj = UserFollowing.objects.filter(
        user=request.user, 
        followed_user=user_to_follow
    ).first()
    
    if following_obj:
        # Usuń obserwację
        following_obj.delete()
        is_following = False
        messages.success(request, f'Przestałeś obserwować użytkownika {username}.')
    else:
        # Dodaj obserwację
        UserFollowing.objects.create(
            user=request.user,
            followed_user=user_to_follow
        )
        is_following = True
        messages.success(request, f'Zacząłeś obserwować użytkownika {username}.')
    
    # Jeśli to żądanie AJAX, zwróć JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'is_following': is_following,
            'followers_count': UserFollowing.objects.filter(followed_user=user_to_follow).count()
        })
    
    # W przeciwnym razie przekieruj z powrotem do profilu użytkownika
    return redirect('accounts:user_profile', username=username)

@login_required
def user_recipes(request):
    """Wyświetla przepisy użytkownika"""
    recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')
    
    context = {
        'recipes': recipes,
        'title': 'Moje przepisy'
    }
    
    return render(request, 'accounts/user_recipes.html', context)

@login_required
def followed_users(request):
    """Wyświetla listę śledzonych użytkowników"""
    # Pobierz użytkowników, których śledzi zalogowany użytkownik
    followed = UserFollowing.objects.filter(user=request.user).select_related('followed_user')
    
    context = {
        'followed_users': followed,
        'title': 'Obserwowani użytkownicy'
    }
    
    return render(request, 'accounts/followed_users.html', context)

@login_required
def followers(request):
    """Wyświetla listę użytkowników obserwujących zalogowanego użytkownika"""
    # Pobierz użytkowników, którzy śledzą zalogowanego użytkownika
    followers = UserFollowing.objects.filter(followed_user=request.user).select_related('user')
    
    # Pobierz ID użytkowników, których obecnie obserwuje zalogowany użytkownik
    following_ids = UserFollowing.objects.filter(user=request.user).values_list('followed_user_id', flat=True)
    
    context = {
        'followers': followers,
        'following_ids': following_ids,
        'title': 'Obserwujący'
    }
    
    return render(request, 'accounts/followers.html', context)

@login_required
def top_users_list(request):
    """Wyświetla listę najpopularniejszych użytkowników"""
    # Użytkownicy z największą liczbą polubień przepisów
    top_liked_users = User.objects.annotate(
        likes_count=Count('recipe__likes')
    ).exclude(
        likes_count=0
    ).order_by('-likes_count')[:10]
    
    # Użytkownicy z największą liczbą przepisów
    most_recipes_users = User.objects.annotate(
        recipes_count=Count('recipe')
    ).exclude(
        recipes_count=0
    ).order_by('-recipes_count')[:10]
    
    # Użytkownicy z największą liczbą obserwujących
    most_followers_users = User.objects.annotate(
        followers_count=Count('followers')
    ).exclude(
        followers_count=0
    ).order_by('-followers_count')[:10]
    
    # Sprawdź, których użytkowników śledzi zalogowany użytkownik
    if request.user.is_authenticated:
        followed_users = UserFollowing.objects.filter(user=request.user).values_list('followed_user_id', flat=True)
    else:
        followed_users = []
    
    context = {
        'top_liked_users': top_liked_users,
        'most_recipes_users': most_recipes_users,
        'most_followers_users': most_followers_users,
        'followed_users': followed_users,
        'title': 'Najpopularniejsi użytkownicy'
    }
    
    return render(request, 'accounts/top_users.html', context)

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
