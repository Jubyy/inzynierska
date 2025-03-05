from django.urls import path
from . import views

urlpatterns = [
    path('', views.shopping_list, name='shopping_list'),
    path('add/', views.add_to_shopping_list, name='add_to_shopping_list'),
    path('print/', views.print_shopping_list, name='print_shopping_list'),
]
