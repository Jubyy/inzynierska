from django.urls import path
from . import views

urlpatterns = [
    path('', views.recipe_list, name='recipe_list'),
    path('add/', views.add_recipe, name='add_recipe'),
    path('<int:recipe_id>/check/', views.check_ingredients, name='check_ingredients'),
    path('<int:recipe_id>/scale/', views.scale_recipe, name='scale_recipe'),

]
