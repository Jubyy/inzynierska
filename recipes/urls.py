from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    # Widoki podstawowe (wyświetlanie, dodawanie, edycja, usuwanie przepisów)
    path('list/', views.RecipeListView.as_view(), name='list'),
    path('detail/<int:pk>/', views.RecipeDetailView.as_view(), name='detail'),
    path('create/', views.RecipeCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.RecipeUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.RecipeDeleteView.as_view(), name='delete'),
    
    # Operacje na przepisach
    path('shopping-list/<int:pk>/', views.add_to_shopping_list, name='add_to_shopping_list'),
    path('missing-ingredients/<int:pk>/', views.add_missing_to_shopping_list, name='add_missing_to_shopping_list'),
    path('prepare/<int:pk>/', views.prepare_recipe, name='prepare_recipe'),
    path('toggle-favorite/<int:pk>/', views.toggle_favorite, name='toggle_favorite'),
    path('toggle-like/<int:pk>/', views.toggle_like, name='toggle_like'),
    
    # Komentarze
    path('delete-comment/<int:pk>/', views.delete_comment, name='delete_comment'),
    
    # Widoki AJAX
    path('api/ingredient-search/', views.ajax_ingredient_search, name='ajax_ingredient_search'),
    path('api/load-units/', views.ajax_load_units, name='ajax_load_units'),
    path('api/add-ingredient/', views.ajax_add_ingredient, name='ajax_add_ingredient'),
    
    # Zarządzanie składnikami
    path('ingredient/list/', views.IngredientListView.as_view(), name='ingredient_list'),
    path('ingredient/create/', views.IngredientCreateView.as_view(), name='ingredient_create'),
    path('ingredient/update/<int:pk>/', views.IngredientUpdateView.as_view(), name='ingredient_update'),
    path('ingredient/delete/<int:pk>/', views.IngredientDeleteView.as_view(), name='ingredient_delete'),
    
    # Planer posiłków
    path('meal-planner/', views.meal_planner, name='meal_planner'),
    path('meal-plan/add/', views.add_meal_plan, name='add_meal_plan'),
    path('meal-plan/add/<str:date_str>/<str:meal_type>/', views.add_meal_plan, name='add_meal_plan_with_params'),
    path('meal-plan/edit/<int:pk>/', views.edit_meal_plan, name='edit_meal_plan'),
    path('meal-plan/delete/<int:pk>/', views.delete_meal_plan, name='delete_meal_plan'),
    path('meal-plan/toggle-completed/<int:pk>/', views.toggle_meal_completed, name='toggle_meal_completed'),
    path('meal-plan/copy-day/<str:from_date>/<str:to_date>/', views.copy_day_meals, name='copy_day_meals'),
    path('meal-plan/generate-shopping-list/', views.generate_shopping_list_from_plan, name='generate_shopping_list_from_plan'),
    path('meal-plan/export-pdf/', views.export_meal_plan_to_pdf, name='export_meal_plan_pdf'),
]
