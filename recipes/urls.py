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
    path('prepare/<int:pk>/', views.prepare_recipe, name='prepare'),
    path('clear-prepared/', views.clear_prepared_recipe, name='clear_prepared_recipe'),
    path('recipes/history/', views.recipe_history, name='history'),
    
    # Operacje na przepisach
    path('shopping-list/<int:pk>/', views.add_to_shopping_list, name='add_to_shopping_list'),
    path('missing-ingredients/<int:pk>/', views.add_missing_to_shopping_list, name='add_missing_to_shopping_list'),
    path('toggle-favorite/<int:pk>/', views.toggle_favorite, name='toggle_favorite'),
    path('toggle-like/<int:pk>/', views.toggle_like, name='toggle_like'),
    
    # Komentarze
    path('delete-comment/<int:pk>/', views.delete_comment, name='delete_comment'),
    
    # Widoki AJAX
    path('api/ingredient-search/', views.ajax_ingredient_search, name='ajax_ingredient_search'),
    path('api/load-units/', views.ajax_load_units, name='ajax_load_units'),
    path('api/load-units-by-type/', views.ajax_load_units_by_type, name='ajax_load_units_by_type'),
    path('api/add-ingredient/', views.ajax_add_ingredient, name='ajax_add_ingredient'),
    path('api/unit-info/', views.ajax_unit_info, name='ajax_unit_info'),
    path('ajax/ingredient-details/', views.ajax_ingredient_details, name='ajax_ingredient_details'),
    
    # Zarządzanie składnikami
    path('ingredient/list/', views.IngredientListView.as_view(), name='ingredient_list'),
    path('ingredient/create/', views.IngredientCreateView.as_view(), name='ingredient_create'),
    path('ingredient/update/<int:pk>/', views.IngredientUpdateView.as_view(), name='ingredient_update'),
    path('ingredient/delete/<int:pk>/', views.IngredientDeleteView.as_view(), name='ingredient_delete'),
    
    # Tablice konwersji i składniki użytkowników
    path('conversions/', views.conversion_tables_list, name='conversion_tables'),
    path('conversions/add/', views.add_conversion_table, name='add_conversion_table'),
    path('conversions/<int:table_id>/', views.conversion_table_detail, name='conversion_table_detail'),
    path('ingredient/submit/', views.submit_ingredient, name='submit_ingredient'),
    path('ingredient/my-submissions/', views.my_ingredient_submissions, name='my_submissions'),
    
    # Admin
    path('admin/pending-ingredients/', views.admin_pending_ingredients, name='admin_pending_ingredients'),
    path('admin/approve-ingredient/<int:ingredient_id>/', views.admin_approve_ingredient, name='admin_approve_ingredient'),
    path('admin/reject-ingredient/<int:ingredient_id>/', views.admin_reject_ingredient, name='admin_reject_ingredient'),
    
    # AJAX
    path('ajax/like/<int:pk>/', views.toggle_like, name='ajax_toggle_like'),
    path('api/search-suggestions/', views.ajax_search_suggestions, name='ajax_search_suggestions'),
    
    # Oceny
    path('rating/<int:pk>/toggle-helpful/', views.toggle_rating_helpful, name='toggle_rating_helpful'),
]
