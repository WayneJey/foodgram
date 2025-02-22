import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from JSON file'

    def handle(self, *args, **kwargs):
        try:
            with open('data/ingredients.json', encoding='utf-8') as file:
                data = json.load(file)
                for item in data:
                    Ingredient.objects.get_or_create(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully loaded {len(data)} ingredients'
                    )
                )
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    'File data/ingredients.json not found'
                )
            )
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR(
                    'Invalid JSON format in data/ingredients.json'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error loading ingredients: {str(e)}'
                )
            )
