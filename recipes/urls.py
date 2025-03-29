from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    # Widoki podstawowe (wyświetlanie, dodawanie, edycja, usuwanie przepisów)
    path('', views.RecipeListView.as_view(), name='list'),
    path('<int:pk>/', views.RecipeDetailView.as_view(), name='detail'),
    path('create/', views.RecipeCreateView.as_view(), name='create'),
    path('<int:pk>/update/', views.RecipeUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.RecipeDeleteView.as_view(), name='delete'),
    
    # Operacje na przepisach
    path('<int:pk>/add-to-shopping-list/', views.add_to_shopping_list, name='add_to_shopping_list'),
    path('<int:pk>/add-missing-to-shopping-list/', views.add_missing_to_shopping_list, name='add_missing_to_shopping_list'),
    path('<int:pk>/prepare/', views.prepare_recipe, name='prepare'),
    path('<int:pk>/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('<int:pk>/toggle-like/', views.toggle_like, name='toggle_like'),
    
    # Komentarze
    path('comments/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    
    # Widoki AJAX
    path('ajax/ingredient-search/', views.ajax_ingredient_search, name='ajax_ingredient_search'),
    path('ajax/load-units/', views.ajax_load_units, name='ajax_load_units'),
    path('ajax/add-ingredient/', views.ajax_add_ingredient, name='ajax_add_ingredient'),
    
    # Zarządzanie składnikami
    path('ingredients/', views.IngredientListView.as_view(), name='ingredient_list'),
    path('ingredients/create/', views.IngredientCreateView.as_view(), name='ingredient_create'),
    path('ingredients/<int:pk>/update/', views.IngredientUpdateView.as_view(), name='ingredient_update'),
    path('ingredients/<int:pk>/delete/', views.IngredientDeleteView.as_view(), name='ingredient_delete'),
]
