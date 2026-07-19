from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# Документация API
@api_view(['GET'])
def manual_docs(request):
    """
    Страница-заглушка с документацией API для дипломной работы.
    Замените пути ниже на реальные из вашего проекта, если они отличаются.
    """
    return Response({
        "Документация API (Ручной режим)": {
            "Авторизация и регистрация": {
                "Регистрация пользователя": "/api/auth/register/",
                "Вход в систему": "/api/auth/login/",
                "Подтверждение Email": "/api/auth/confirm-email/",
                "Повторная отправка кода": "/api/auth/resend-confirmation/",
            },
            "Каталог товаров": {
                "Список товаров": "/api/products/",
                "Список категорий": "/api/categories/",
                "Список магазинов": "/api/stores/",
            },
            "Личный кабинет": {
                "Управление контактами": "/api/contacts/",
                "История заказов": "/api/orders/",
            },
            "Корзина": {
                "Просмотр корзины": "/api/cart/my_cart/",
                "Добавить товар": "/api/cart/add_item/",
                "Удалить товар": "/api/cart/remove_item/",
                "Подтвердить заказ": "/api/cart/confirm/",
            },
            "Загрузка прайсов (для поставщика)": {
                "Эндпоинт загрузки YAML": "/api/upload/",
            }
        }
    })

urlpatterns += [
    # Ссылка на документацию
    path('docs/', manual_docs, name='manual-docs'),
]

# Отдача медиафайлов (картинок товаров) в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)