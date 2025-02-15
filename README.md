![CI/CD](https://github.com/Waynejey/foodgram/actions/workflows/main.yml/badge.svg)

# Foodgram

## Описание проекта

Foodgram — это веб-приложение для обмена рецептами с функционалом для добавления рецептов в избранное, формирования списка покупок и подписки на пользователей.

## Стек технологий

- **Backend**: Python 3, Django, Django Rest Framework (DRF)
- **Аутентификация**: Djoser
- **База данных**: PostgreSQL / SQLite (для локального тестирования)
- **Контейнеризация**: Docker, Docker Compose
- **Веб-сервер**: Nginx
- **CI/CD**: GitHub Actions

## Развертывание проекта

Клонируем репозиторий

```bash
git clone https://github.com/WayneJey/foodgram.git
```


## Переменные окружения `.env`
Создайте в корне проекта файл .env в формате:

```ini
POSTGRES_USER=django_user # Логин для подключения к базе данных
POSTGRES_PASSWORD=mysecretpassword # Пароль для подключения к базе данных
POSTGRES_DB=django # Имя базы данных
DB_HOST=db # Название контейнера базы данных
DB_PORT=5432  # Порт для подключения к базе данных

DEBUG=False # True для включения режима отладки, False для продакшн-среды
ALLOWED_HOSTS=yourdomain.com,localhost,127.0.0.1 # Укажите ваш хост
CSRF_TRUSTED_ORIGINS= # Доверенные источники для CSRF
USE_SQLITE=True # True для использования SQLite, False для использования PostgreSQL
SECRET_KEY= # Секретный ключ Django
```

### Запуск через Docker

```bash
# Запускаем контейнеры
sudo docker compose -f docker-compose.production.yml up -d
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic --no-input
sudo docker compose -f docker-compose.production.yml exec backend python manage.py load_ingredients
sudo docker compose -f docker-compose.production.yml exec backend python manage.py load_tags
```

## Автор

**Waynejey** - разработчик проекта.


## Информация для ревьюера

- **Сайт**: https://foodgramwayne.zapto.org

- **Админка**
- **Логин**: waynejey@yandex.ru
- **Пароль**: wayne

Коллекцию postman провел, все гуд. Прошелся по чек листам, тоже все нормально