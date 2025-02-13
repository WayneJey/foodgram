from django.core.management.base import BaseCommand
from recipes.models import Tag


class Command(BaseCommand):
    help = 'Creates initial tags'

    def handle(self, *args, **kwargs):
        tags_data = [
            {'name': 'Завтрак', 'slug': 'breakfast', 'color': '#E26C2D'},
            {'name': 'Обед', 'slug': 'lunch', 'color': '#49B64E'},
            {'name': 'Ужин', 'slug': 'dinner', 'color': '#8775D2'}
        ]

        for tag_data in tags_data:
            Tag.objects.get_or_create(
                slug=tag_data['slug'],
                defaults=tag_data
            )

        self.stdout.write(self.style.SUCCESS('Successfully created tags'))
