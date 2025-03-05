from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', accounts_views.register, name='register'),
    path('dashboard/', accounts_views.dashboard, name='dashboard'),
    # Logowanie i wylogowanie (Django Auth)
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', accounts_views.custom_logout, name='logout'),
    path('fridge/', include('fridge.urls')),
    path('recipes/', include('recipes.urls')),

]
