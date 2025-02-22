import base64
import uuid

import six
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, six.string_types):
            if 'data:' in data and ';base64,' in data:
                header, data = data.split(';base64,')
            try:
                decoded_file = base64.b64decode(data)
            except TypeError:
                self.fail('invalid_image')

            file_name = str(uuid.uuid4())[:12]
            file_extension = self.get_file_extension(file_name, decoded_file)
            complete_file_name = f"{file_name}.{file_extension}"
            data = ContentFile(decoded_file, name=complete_file_name)

        return super().to_internal_value(data)

    def get_file_extension(self, file_name, decoded_file):
        import imghdr
        extension = imghdr.what(file_name, decoded_file)
        extension = "jpg" if extension == "jpeg" else extension
        return extension


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    avatar = Base64ImageField(required=False, allow_null=True)

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

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['id'] = ret.get('id', 0)
        ret['username'] = ret.get('username', '')
        ret['first_name'] = ret.get('first_name', '')
        ret['last_name'] = ret.get('last_name', '')
        ret['email'] = ret.get('email', '')
        ret['is_subscribed'] = ret.get('is_subscribed', False)
        ret['avatar'] = ret.get('avatar', '')
        return ret


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if data['avatar'] is None:
            data['avatar'] = ''
        elif request is not None:
            data['avatar'] = request.build_absolute_uri(data['avatar'])
        return data


class RecipeShortSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]
        return RecipeMinifiedSerializer(recipes, many=True).data


class SubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id',)

    def validate(self, data):
        user = self.context['request'].user
        author = self.instance

        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )

        if user.subscriptions.filter(author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя'
            )

        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return SubscriptionSerializer(
            instance,
            context={'request': request}
        ).data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author = UserSerializer()
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField()
        ),
        write_only=True,
        required=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image',
            'name', 'text', 'cooking_time'
        )

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Нужен хотя бы один ингредиент'
            )

        ingredients_set = set()
        for item in value:
            ingredient_id = item.get('id')
            if not ingredient_id:
                raise serializers.ValidationError(
                    'Отсутствует id ингредиента'
                )

            if ingredient_id in ingredients_set:
                raise serializers.ValidationError(
                    'Ингредиенты не должны повторяться'
                )
            ingredients_set.add(ingredient_id)

            amount = item.get('amount')
            if not amount or not isinstance(amount, int) or amount < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть целым числом больше 0'
                )
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                'Нужен хотя бы один тег'
            )

        tag_ids = [tag.id for tag in value]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                'Теги не должны повторяться'
            )

        return value

    def update_tags_and_ingredients(self, recipe, tags_data, ingredients_data):
        recipe.tags.set(tags_data)

        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient_item['id'],
                amount=ingredient_item['amount']
            )
            for ingredient_item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        self.update_tags_and_ingredients(recipe, tags_data, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        instance.recipe_ingredients.all().delete()
        self.update_tags_and_ingredients(instance, tags_data, ingredients_data)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        serializer = RecipeSerializer(
            instance,
            context=self.context
        )
        return serializer.data


class RecipeListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = serializers.SerializerMethodField()
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_author(self, obj):
        return UserSerializer(
            obj.author,
            context={'request': self.context.get('request')}
        ).data

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return obj.favorites.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return obj.shopping_cart.filter(user=user).exists()

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None
