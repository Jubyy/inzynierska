from django.urls import path
from . import views

urlpatterns = [
    path('', views.fridge_list, name='fridge_list'),
    path('add/', views.add_fridge_item, name='add_fridge_item'),
]
