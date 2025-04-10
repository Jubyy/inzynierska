from django.urls import path
from . import views

app_name = 'fridge'

urlpatterns = [
    # Widoki podstawowe lodówki
    path('', views.fridge_dashboard, name='dashboard'),
    path('list/', views.FridgeItemListView.as_view(), name='list'),
    
    # Zarządzanie produktami w lodówce
    path('add/', views.FridgeItemCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.FridgeItemUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.FridgeItemDeleteView.as_view(), name='delete'),
    
    # Dodatkowe funkcje
    path('bulk-add/', views.bulk_add_to_fridge, name='bulk_add'),
    path('clean-expired/', views.clean_expired, name='clean_expired'),
    path('available-recipes/', views.available_recipes, name='available_recipes'),
    
    # Widoki AJAX
    path('ajax/ingredient-search/', views.ajax_ingredient_search, name='ajax_ingredient_search'),
    path('ajax/load-units/', views.ajax_load_units, name='ajax_load_units'),
    path('ajax/compatible-units/', views.ajax_compatible_units, name='ajax_compatible_units'),
    path('consolidate/', views.consolidate_items, name='consolidate'),
]
