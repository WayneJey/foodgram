import base64
from io import BytesIO

import shortuuid
from django.core.files.base import ContentFile
from django.db.models import Count, Exists, OuterRef, Sum, Value
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomPagination
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeMinifiedSerializer,
    RecipeSerializer,
    SubscribeSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserAvatarSerializer,
    UserSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Follow, User


def decode_base64_image(base64_string):
    """Декодирует base64 в файл изображения."""
    format, imgstr = base64_string.split(';base64,')
    ext = format.split('/')[-1]
    return ContentFile(
        base64.b64decode(imgstr),
        name=f'recipe.{ext}'
    )


def create_shopping_list_file(ingredients):
    """Создает файл со списком покупок и возвращает буфер BytesIO."""
    shopping_list = "Список покупок:\n"
    for ingredient in ingredients:
        shopping_list += (
            f"{ingredient['ingredient__name']} - "
            f"{ingredient['total']} "
            f"{ingredient['ingredient__measurement_unit']}\n"
        )
    buffer = BytesIO()
    buffer.write(shopping_list.encode('utf-8'))
    buffer.seek(0)
    return buffer


def handle_recipe_relation(request, pk, model_class, serializer_class):
    """Обрабатывает добавление/удаление рецепта в избранное или корзину."""
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, id=pk)
        if model_class.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists():
            return Response(
                {'errors': 'Объект уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        model_class.objects.create(user=request.user, recipe=recipe)
        serializer = RecipeMinifiedSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    get_object_or_404(Recipe, id=pk)

    deleted, _ = model_class.objects.filter(
        user=request.user, recipe_id=pk
    ).delete()
    if deleted:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(
        {'errors': 'Объект не найден'},
        status=status.HTTP_400_BAD_REQUEST
    )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с тегами."""
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Tag.objects.all()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с ингредиентами."""
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Ingredient.objects.all()


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами."""

    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update', 'update']:
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.select_related(
            'author').prefetch_related('tags', 'ingredients')

        if user.is_authenticated:
            return queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                )
            )
        return queryset.annotate(
            is_favorited=Value(False),
            is_in_shopping_cart=Value(False)
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[AllowAny]
    )
    def get_link(self, request, pk=None):
        short_uuid = shortuuid.uuid()[:8]
        short_link = f"http://{request.get_host()}/r/{short_uuid}"

        return Response(
            {'short-link': short_link},
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return handle_recipe_relation(
            request, pk, Favorite, RecipeMinifiedSerializer
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return handle_recipe_relation(
            request, pk, ShoppingCart, RecipeMinifiedSerializer
        )

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = RecipeIngredient.objects.filter(
            recipe__shoppingcarts__user=user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(total=Sum('amount'))

        shopping_list_file = create_shopping_list_file(ingredients)
        response = HttpResponse(shopping_list_file, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""
    serializer_class = UserSerializer
    pagination_class = CustomPagination
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        return User.objects.annotate(recipes_count=Count('recipes'))

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = UserSerializer(
            request.user,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
        url_name='me_avatar'
    )
    def me_avatar(self, request):
        user = request.user

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'error': 'Аватар не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )

        avatar_data = request.data.get('avatar')
        if not avatar_data:
            return Response(
                {'error': 'Не предоставлен файл аватара'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if isinstance(avatar_data, str) and avatar_data.startswith(
            'data:image'
        ):
            _, imgstr = avatar_data.split(';base64,')  # Split at most once
            imgdata = base64.b64decode(imgstr)
            image = ContentFile(imgdata)
            user.avatar.save(f'{user.id}_avatar.png', image)
            serializer = UserAvatarSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Неверный формат аватара'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        user = request.user

        if request.method == 'POST':
            author = get_object_or_404(User, id=id)

            serializer = SubscribeSerializer(
                author,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            Follow.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        author = get_object_or_404(User, id=id)
        deleted, _ = Follow.objects.filter(user=user, author_id=id).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Подписка не найдена'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user).annotate(
            recipes_count=Count('recipes'))
        pages = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
