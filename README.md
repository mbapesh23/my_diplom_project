# Backend API: Дипломная работа профессии "Python-разработчик"

RESTful API сервис для управления каталогом товаров, заказами и пользователями. Проект разработан на Python с использованием фреймворка Django и Django REST Framework.

## Оглавление
- [Backend API: Дипломная работа профессии "Python-разработчик"](#backend-api-дипломная-работа-профессии-python-разработчик)
  - [Оглавление](#оглавление)
  - [Функционал](#функционал)
  - [Технологический стек](#технологический-стек)
  - [Структура проекта](#структура-проекта)
  - [Установка и запуск локально](#установка-и-запуск-локально)
    - [Клонирование репозитория](#клонирование-репозитория)

## Функционал
* Регистрация пользователей с обязательной email-верификацией (подтверждением).
* JWT-аутентификация (access и refresh токены).
* Управление профилями пользователей и адресами доставки (контактами).
* Каталогизация товаров по категориям и магазинам (витринам).
* Сложная структура цен: базовая цена, рекомендованная розничная цена (РРЦ) и параметры товара (цвет, память).
* Работа с корзиной пользователя через модель черновика заказа.
* Создание заказов со статусной моделью (NEW $\rightarrow$ AWAITING_PAYMENT $\rightarrow$ DELIVERED).
* Автоматизированное наполнение базы данных из единого YAML-файла.

## Технологический стек
* **Язык:** Python 3.13+
* **Фреймворк:** Django 6.0.1
* **API:** Django REST Framework 3.17.1
* **Аутентификация:** djangorestframework-simplejwt 5.5.1
* **База данных:** SQLite 3 (в разработке), поддержка PostgreSQL (через psycopg2-binary)
* **CORS:** django-cors-headers
* **Веб-сервер:** Uvicorn (ASGI)
* **Управление окружением:** python-dotenv

## Структура проекта
my_diplom_project/
├── api/                      # Основное приложение бизнес-логики
│   ├── migrations/
│   ├── models.py             # Модели User, Shop, Product, Order, Contact
│   ├── serializers.py        # Сериализаторы DRF (валидация ввода/вывода)
│   ├── views.py              # ViewSet'ы и APIView (регистрация, вход)
│   └── urls.py               # Роутинг API
├── diploma_backend/          # Корневая конфигурация Django
│   ├── settings.py           # Настройки БД, CORS, Email
│   ├── asgi.py               # ASGI точка входа (для uvicorn)
│   └── wsgi.py               # WSGI точка входа
├── media/                    # prices.yaml
│   └── prices.yaml
├── .env                      # Шаблон переменных окружения
├── .gitignore                # Исключенные файлы (venv/, pycache/)
├── manage.py                 # Утилита командной строки Django
├── requirements.txt          # Зависимости Python
├── run_loader.py             # Скрипт загрузки данных из YAML
└── README.md                 # Данный файл


## Установка и запуск локально

### Клонирование репозитория
```bash
git clone https://github.com/mbapesh23/my_diplom_project.git
cd my_diplom_project
Создание виртуального окружения
Важно: папка виртуального окружения добавлена в .gitignore.

Для Windows (PowerShell):

python -m venv venv
.\venv\Scripts\Activate.ps1
(Для Linux/macOS используйте source venv/bin/activate)

Установка зависимостей

pip install --upgrade pip
pip install -r requirements.txt
Настройка переменных окружения

Создайте в корне проекта файл .env на основе шаблона:

.env.example .env
(На Linux/macOS: cp .env.example .env)

Применение миграций
Создание таблиц в базе данных:


python manage.py migrate
Создание суперпользователя

python manage.py createsuperuser
Запуск сервера разработки

uvicorn diploma_backend.asgi:application --reload
Сервер будет доступен по адресу http://127.0.0.1:8000.

Переменные окружения (.env)
Обязательные переменные для работы приложения:

env

DJANGO_SECRET_KEY=your-secret-key-generate-it-with-python-manage.py-check-deploy
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_SSL=False
PAYMENT_API_TOKEN=your_token_here

Описание API
Базовый URL: http://127.0.0.1:8000/api/

Метод	Эндпоинт	Назначение
POST	/register/	Регистрация нового пользователя. Создает неактивного пользователя и отправляет код подтверждения.
POST	/confirm-email/	Активация аккаунта по коду из письма.
POST	/login/	Получение пары JWT-токенов (доступен только после подтверждения почты).
GET	/stores/	Список всех магазинов (витрин). Публичный доступ.
GET	/categories/	Список категорий товаров. Публичный доступ.
GET	/products/	Поиск и фильтрация товаров.
GET	/contacts/	Список адресов доставки текущего пользователя. Требуется авторизация.
POST	/contacts/	Добавление нового адреса доставки.
GET	/cart/	Просмотр текущей корзины (заказа со статусом NEW).
POST	/cart/	Добавление позиции в корзину.
PATCH/PUT	/orders/{id}/	Изменение статуса заказа или привязка контакта.
Примечание: Для доступа к защищенным маршрутам добавьте заголовок Authorization: Bearer <access_token>.

Работа с базой данных и миграции
Проект использует SQLite3 для локальной разработки. Все изменения структуры БД фиксируются через систему миграций:

python manage.py makemigrations
python manage.py migrate

Тестирование
Запуск юнит-тестов:
python manage.py test api


Административная панель
Доступна по адресу http://127.0.0.1:8000/admin/. 
Учетная запись администратора создается командой createsuperuser. В панели доступны все сущности: Пользователи, Магазины, Товары, Цены, Заказы.

Загрузка данных
Скрипт run_loader.py предназначен для полного сброса тестового стенда и наполнения базы данными из файла media/prices.yaml. Скрипт поддерживает идемпотентность (данные можно загружать повторно — они будут обновляться, а не дублироваться).

Запуск:

python run_loader.py
Пример структуры файла prices.yaml:

yaml

users:
  - username: "buyer"
    email: "client@example.com"
    password: "qwerty"
store: "Default Marketplace"
categories:
  - id: 1
    name: "Электроника"
goods:
  - id: "SKU-001"
    name: "Смартфон X"
    price: 50000.00
    quantity: 10
orders:
  - user: "buyer"
    status: "NEW"
    items:
      - product_info_id: "SKU-001"
        quantity: 1
        price_at_order: 50000.00