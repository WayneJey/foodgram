from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Tag, Ingredient, Recipe,
    RecipeIngredient, Favorite,
    ShoppingCart
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    ordering = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)
    ordering = ('name',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1
    extra = 1
    raw_id_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author',
        'get_image_preview', 'get_favorites_count'
    )
    search_fields = ('name', 'author__username', 'tags__name')
    list_filter = ('tags', 'author')
    inlines = (RecipeIngredientInline,)
    raw_id_fields = ('author',)

    def get_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px;">',
                obj.image.url
            )
        return 'Нет изображения'
    get_image_preview.short_description = 'Изображение'

    def get_favorites_count(self, obj):
        return obj.favorites.count()
    get_favorites_count.short_description = 'В избранном'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = (
        'user__username',
        'user__email',
        'recipe__name'
    )


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = (
        'user__username',
        'user__email',
        'recipe__name'
    )

# Регистрация модели RecipeIngredient отдельно, если нужен доступ к ней


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')
