from django.urls import path
from . import views
from django.urls import reverse_lazy
from django.views.generic import RedirectView

app_name = 'fridge'

urlpatterns = [
    # Widoki podstawowe lodówki
    path('', views.fridge_dashboard, name='dashboard'),
    path('list/', views.FridgeItemListView.as_view(), name='list'),
    
    # Zarządzanie produktami w lodówce
    path('add/', views.FridgeItemCreateView.as_view(), name='add'),
    path('update/<int:pk>/', views.FridgeItemUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.FridgeItemDeleteView.as_view(), name='delete'),
    
    # Dodatkowe funkcje
    path('bulk-add/', views.bulk_add_to_fridge, name='bulk_add'),
    path('clean-expired/', views.clean_expired, name='clean_expired'),
    path('available-recipes/', views.available_recipes, name='available_recipes'),
    
    # Widoki AJAX
    path('ajax/ingredient-search/', views.ajax_ingredient_search, name='ajax_ingredient_search'),
    path('ajax/load-units/', views.ajax_load_units, name='ajax_load_units'),
    path('ajax/compatible-units/', views.ajax_compatible_units, name='ajax_compatible_units'),
    path('ajax/convert/', views.ajax_convert_units, name='ajax_convert_units'),
    path('consolidate/', views.consolidate_items, name='consolidate'),
    
    # Przekierowania dla starych ścieżek konwersji
    path('conversions/', RedirectView.as_view(url=reverse_lazy('recipes:conversion_tables')), name='conversion_dashboard'),
    path('conversions/ingredient/<int:ingredient_id>/', RedirectView.as_view(url=reverse_lazy('recipes:conversion_tables')), name='ingredient_conversions'),
    path('conversions/add/<int:ingredient_id>/', RedirectView.as_view(url=reverse_lazy('recipes:conversion_tables')), name='add_conversion'),
    path('conversions/edit/<int:conversion_id>/', RedirectView.as_view(url=reverse_lazy('recipes:conversion_tables')), name='edit_conversion'),
    path('conversions/delete/<int:conversion_id>/', RedirectView.as_view(url=reverse_lazy('recipes:conversion_tables')), name='delete_conversion'),
    path('conversions/update-params/<int:ingredient_id>/', RedirectView.as_view(url=reverse_lazy('recipes:conversion_tables')), name='update_params'),
]
