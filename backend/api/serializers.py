from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name',
            'email', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return request.user.subscriptions.filter(author=obj).exists()

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return ''  # Возвращаем пустую строку вместо None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Убедимся, что все поля присутствуют и имеют правильный тип
        ret['id'] = ret.get('id', 0)
        ret['username'] = ret.get('username', '')
        ret['first_name'] = ret.get('first_name', '')
        ret['last_name'] = ret.get('last_name', '')
        ret['email'] = ret.get('email', '')
        ret['is_subscribed'] = ret.get('is_subscribed', False)
        ret['avatar'] = ret.get('avatar', '')  # Пустая строка по умолчанию
        return ret
