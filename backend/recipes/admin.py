from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    list_display_links = ('name', 'slug')
    search_fields = ('name', 'slug')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    list_display_links = ('name',)
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = 1
    extra = 1


class TagFilter(AutocompleteFilter):
    title = 'Тег'
    field_name = 'tags'


class AuthorFilter(AutocompleteFilter):
    title = 'Автор'
    field_name = 'author'


class UserFilter(AutocompleteFilter):
    title = 'Пользователь'
    field_name = 'user'


class RecipeFilter(AutocompleteFilter):
    title = 'Рецепт'
    field_name = 'recipe'


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorites_count')
    list_display_links = ('name', 'author')
    list_filter = (AuthorFilter, TagFilter)
    search_fields = ('name',)
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('author').prefetch_related(
            'tags',
            'ingredients',
            'favorites'
        )

    def favorites_count(self, obj):
        return obj.favorites.count()
    favorites_count.short_description = 'В избранном'

    class Media:
        pass


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')
    list_display_links = ('user', 'recipe')
    list_filter = (UserFilter, RecipeFilter)
    search_fields = ()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')
    list_display_links = ('user', 'recipe')
    list_filter = (UserFilter, RecipeFilter)
    search_fields = ()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'recipe')


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    list_display_links = ('recipe', 'ingredient')
    list_filter = (RecipeFilter,)
    search_fields = ()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('recipe', 'ingredient')
