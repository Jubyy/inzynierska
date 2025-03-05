from django.urls import path
from . import views

urlpatterns = [
    path('', views.recipe_list, name='recipe_list'),
    path('add/', views.add_recipe, name='add_recipe'),
    path('<int:recipe_id>/check/', views.check_ingredients, name='check_ingredients'),
    path('<int:recipe_id>/scale/', views.scale_recipe, name='scale_recipe'),
    path('<int:recipe_id>/edit/', views.edit_recipe, name='edit_recipe'),
    path('<int:recipe_id>/delete/', views.delete_recipe, name='delete_recipe'),
    path('<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('search/', views.search_recipes, name='search_recipes'),
    path('<int:recipe_id>/prepare/', views.prepare_meal, name='prepare_meal'),


]
