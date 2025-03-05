from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', accounts_views.register, name='register'),
    path('dashboard/', accounts_views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', accounts_views.custom_logout, name='logout'),
    path('fridge/', include('fridge.urls')),
    path('recipes/', include('recipes.urls')),
    path('accounts/', include('accounts.urls')),

]

# 🔥 DODAJ TO NA SAMYM DOLE:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
