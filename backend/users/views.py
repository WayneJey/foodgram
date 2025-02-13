import base64

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from djoser.views import UserViewSet

from api.serializers import UserSerializer
from .models import Follow, User
from .serializers import (
    SubscriptionSerializer, SubscribeSerializer, UserAvatarSerializer
)
from api.pagination import CustomPagination


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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
                user.avatar = None
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response(
                {'error': 'Аватар не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'PUT':
            avatar_data = request.data.get('avatar', None)

            if not avatar_data:
                return Response(
                    {'error': 'Не предоставлен файл аватара'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                if avatar_data.startswith('data:image'):
                    format, imgstr = avatar_data.split(';base64,')
                    imgdata = base64.b64decode(imgstr)
                    image = ContentFile(imgdata)
                    user.avatar.save(f'{user.id}_avatar.png', image, save=True)
                    user.save()

                    serializer = UserAvatarSerializer(user)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    raise ValidationError("Неверный формат аватара")
            except (ValueError, TypeError, ValidationError) as e:
                return Response(
                    {'error': str(e)}, status=status.HTTP_400_BAD_REQUEST
                )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        user = request.user
        try:
            author = User.objects.get(id=id)
        except User.DoesNotExist:
            return Response(
                {'errors': 'Автор не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'POST':
            serializer = SubscribeSerializer(
                author,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            Follow.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        try:
            subscription = Follow.objects.get(user=user, author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Follow.DoesNotExist:
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
        queryset = User.objects.filter(following__user=user)
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
