import base64
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Tag, Ingredient, Recipe, Favorite,
    ShoppingCart, RecipeIngredient
)
from .serializers import (
    TagSerializer, IngredientSerializer,
    RecipeCreateUpdateSerializer, RecipeListSerializer,
    RecipeMinifiedSerializer
)
from .permissions import IsAuthorOrReadOnly


def decode_base64_image(base64_string):
    """Декодирует base64 в файл изображения."""
    format, imgstr = base64_string.split(';base64,')
    ext = format.split('/')[-1]
    return ContentFile(
        base64.b64decode(imgstr),
        name=f'recipe.{ext}'
    )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с тегами."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с ингредиентами."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            return queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами."""
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action in ('create', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        author = self.request.query_params.get('author')
        if author:
            queryset = queryset.filter(author_id=author)

        user = self.request.user
        if user.is_authenticated:
            is_favorited = self.request.query_params.get('is_favorited')
            is_in_shopping_cart = self.request.query_params.get(
                'is_in_shopping_cart'
            )

            if is_favorited == '1':
                queryset = queryset.filter(favorites__user=user)
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(shopping_cart__user=user)

        return queryset

    def perform_create(self, serializer):
        image_data = serializer.validated_data.pop('image')
        image_file = decode_base64_image(image_data)
        recipe = serializer.save(
            author=self.request.user,
            image=image_file
        )
        self._save_recipe_ingredients(
            recipe,
            serializer.validated_data['ingredients']
        )

    def perform_update(self, serializer):
        image_data = serializer.validated_data.get('image')
        recipe = serializer.instance

        if image_data:
            image_file = decode_base64_image(image_data)
            recipe.image = image_file

        recipe.recipe_ingredients.all().delete()
        recipe = serializer.save()
        self._save_recipe_ingredients(
            recipe,
            serializer.validated_data['ingredients']
        )

    def _save_recipe_ingredients(self, recipe, ingredients_data):
        """Сохраняет ингредиенты для рецепта."""
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient_item['id'],
                amount=ingredient_item['amount']
            )
            for ingredient_item in ingredients_data
        ])

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное."""
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeMinifiedSerializer(
                recipe,
                context={'request': request}
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        favorite = get_object_or_404(
            Favorite,
            user=request.user,
            recipe=recipe
        )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в список покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeMinifiedSerializer(
                recipe,
                context={'request': request}
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        shopping_cart = get_object_or_404(
            ShoppingCart,
            user=request.user,
            recipe=recipe
        )
        shopping_cart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачивание списка покупок."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount'))

        shopping_list = ['Список покупок:\n\n']
        for item in ingredients:
            shopping_list.append(
                f'- {item["ingredient__name"]} '
                f'({item["ingredient__measurement_unit"]}) '
                f'- {item["total_amount"]}\n'
            )

        response = FileResponse(
            '\n'.join(shopping_list).encode(),
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response
