from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import (
    EMAIL_MAX_LENGTH,
    FIRST_NAME_MAX_LENGTH,
    LAST_NAME_MAX_LENGTH,
)


class User(AbstractUser):
    """Пользователь с дополнительными полями."""

    email = models.EmailField(
        'Email',
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
    )
    first_name = models.CharField(
        'Имя',
        max_length=FIRST_NAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=LAST_NAME_MAX_LENGTH,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        blank=True,
        default=''
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['id']

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Подписка на авторов."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow'
            )
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
