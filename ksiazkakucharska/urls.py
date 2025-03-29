from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views
from recipes.views import RecipeListView
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Strona główna
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # Aplikacje
    path('accounts/', include('accounts.urls')),
    path('recipes/', include('recipes.urls')),
    path('fridge/', include('fridge.urls')),
    path('shopping/', include('shopping.urls')),
    
    # Podstawowe widoki kont (dla wygody)
    path('register/', accounts_views.register, name='register'),
    path('login/', include('django.contrib.auth.urls')),
    path('dashboard/', accounts_views.dashboard, name='dashboard'),
    path('logout/', accounts_views.custom_logout, name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
