from django.urls import path
from . import views

urlpatterns = [
    path('', views.fridge_list, name='fridge_list'),
    path('add/', views.add_fridge_item, name='add_fridge_item'),
    path('<int:item_id>/edit/', views.edit_fridge_item, name='edit_fridge_item'),
path('<int:item_id>/delete/', views.delete_fridge_item, name='delete_fridge_item'),
]
