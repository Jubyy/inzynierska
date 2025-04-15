from django.urls import path
from . import views

app_name = 'shopping'

urlpatterns = [
    # Widoki list zakupów
    path('', views.ShoppingListListView.as_view(), name='list'),
    path('<int:pk>/', views.ShoppingListDetailView.as_view(), name='detail'),
    path('create/', views.ShoppingListCreateView.as_view(), name='create'),
    path('<int:pk>/update/', views.ShoppingListUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ShoppingListDeleteView.as_view(), name='delete'),
    
    # Zarządzanie pozycjami na liście zakupów
    path('<int:pk>/add/', views.add_shopping_item, name='add_item'),
    path('item/<int:pk>/edit/', views.edit_shopping_item, name='edit_item'),
    path('item/<int:pk>/delete/', views.delete_shopping_item, name='delete_item'),
    path('item/<int:pk>/toggle/', views.toggle_purchased, name='toggle_purchased'),
    
    # Dodatkowe funkcje
    path('<int:pk>/complete/', views.complete_shopping, name='complete'),
    path('create-from-recipe/', views.create_from_recipe, name='create_from_recipe'),
    
    # Widoki AJAX
    path('ajax/ingredient-search/', views.ajax_ingredient_search, name='ajax_ingredient_search'),
    path('ajax/load-units/', views.ajax_load_units, name='ajax_load_units'),
    path('list/<int:pk>/export-pdf/', views.export_list_to_pdf, name='export_pdf'),
    path('<int:pk>/normalize/', views.normalize_shopping_list, name='normalize'),
]
