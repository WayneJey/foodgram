from django.urls import path, include
from rest_framework.routers import DefaultRouter
from recipes.views import (
    TagViewSet, IngredientViewSet,
    RecipeViewSet
)
from users.views import CustomUserViewSet

app_name = 'api'

router = DefaultRouter()
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('users', CustomUserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
