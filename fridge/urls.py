from django.urls import path
from . import views
from django.urls import reverse_lazy
from django.views.generic import RedirectView

app_name = 'fridge'

urlpatterns = [
    # Główne widoki lodówki
    path('', views.fridge_dashboard, name='dashboard'),
    path('list/', views.FridgeItemListView.as_view(), name='list'),
    path('add/', views.FridgeItemCreateView.as_view(), name='add'),
    path('update/<int:pk>/', views.FridgeItemUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.FridgeItemDeleteView.as_view(), name='delete'),
    path('bulk-add/', views.bulk_add_to_fridge, name='bulk_add'),
    path('clean-expired/', views.clean_expired, name='clean_expired'),
    path('available-recipes/', views.available_recipes, name='available_recipes'),
    
    # Usunięto: ścieżki związane z konsolidacją, eksportem i importem
    
    # AJAX i API
    path('ajax/ingredient-search/', views.ajax_ingredient_search, name='ajax_ingredient_search'),
    path('ajax/load-units/', views.ajax_load_units, name='ajax_load_units'),
    path('ajax/compatible-units/', views.ajax_compatible_units, name='ajax_compatible_units'),
    path('ajax/convert-units/', views.ajax_convert_units, name='ajax_convert_units'),
    path('ajax/add-to-fridge/', views.ajax_add_to_fridge, name='ajax_add_to_fridge'),
    
    # Konwersje jednostek
    path('conversions/', views.conversion_dashboard, name='conversion_dashboard'),
    path('conversions/ingredient/<int:ingredient_id>/', views.ingredient_conversions, name='ingredient_conversions'),
    path('conversions/add/<int:ingredient_id>/', views.add_conversion, name='add_conversion'),
    path('conversions/edit/<int:conversion_id>/', views.edit_conversion, name='edit_conversion'),
    path('conversions/delete/<int:conversion_id>/', views.delete_conversion, name='delete_conversion'),
    path('conversions/update-params/<int:ingredient_id>/', views.update_ingredient_params, name='update_ingredient_params'),
    
    # Powiadomienia
    path('notifications/check/', views.check_notifications, name='check_notifications'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/delete/<int:pk>/', views.delete_notification, name='delete_notification'),
    path('notifications/delete_all/', views.delete_all_notifications, name='delete_all_notifications'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark_all_read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
