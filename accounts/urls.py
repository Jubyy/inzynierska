from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm, CustomPasswordChangeForm

app_name = 'accounts'

urlpatterns = [
    # Podstawowe widoki kont
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        authentication_form=CustomAuthenticationForm
    ), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Aktywacja konta
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate'),
    path('activation-sent/', views.activation_sent, name='activation_sent'),
    
    # Profil użytkownika
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/recipes/', views.user_recipes, name='user_recipes'),
    
    # Zmiana hasła
    path('profile/change-password/', 
         auth_views.PasswordChangeView.as_view(
             template_name='accounts/change_password.html',
             form_class=CustomPasswordChangeForm,
             success_url='/accounts/profile/'
         ), 
         name='change_password'),
    
    # Śledzenie użytkowników
    path('community/', views.top_users_list, name='top_users'),
    path('user/<str:username>/', views.user_profile_view, name='user_profile'),
    path('user/<str:username>/follow/', views.toggle_follow, name='toggle_follow'),
    path('following/', views.followed_users, name='following'),
    path('followers/', views.followers, name='followers'),
    
    # Resetowanie hasła
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             success_url='/accounts/password-reset/done/'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
