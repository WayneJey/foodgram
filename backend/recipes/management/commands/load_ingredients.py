import json
import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из JSON или CSV файла'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            nargs='?',
            default=os.path.join(settings.BASE_DIR, 'data', 'ingredients.csv'),
            help='Путь к файлу (JSON или CSV)'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        self.stdout.write(f'Загрузка ингредиентов из файла: {file_path}')

        try:
            ingredients_data = []
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as file:
                    ingredients_data = json.load(file)

            elif file_ext == '.csv':
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    ingredients_data = [
                        {'name': row[0], 'measurement_unit': row[1]}
                        for row in reader
                    ]
            else:
                raise ValueError(
                    'Неподдерживаемый формат файла. '
                    'Используйте JSON или CSV'
                )

            ingredients_to_create = [
                Ingredient(
                    name=item['name'],
                    measurement_unit=item['measurement_unit']
                )
                for item in ingredients_data
            ]

            Ingredient.objects.bulk_create(
                ingredients_to_create,
                ignore_conflicts=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Успешно загружено {len(ingredients_to_create)} ингредиентов'
                )
            )

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    f'Файл {file_path} не найден. '
                    f'Убедитесь, что файл существует в указанной директории'
                )
            )
        except (json.JSONDecodeError, csv.Error) as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Ошибка при чтении файла {file_path}: {str(e)}'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Произошла ошибка: {str(e)}')
            )
