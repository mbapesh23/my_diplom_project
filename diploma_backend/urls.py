from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.views import APIView
from rest_framework.response import Response

urlpatterns = [
    # Административная панель Django
    path('admin/', admin.site.urls),
    
    # Все эндпоинты вашего приложения (products, stores/categories)
    path('api/', include('api.urls')),
]

# --- ДОКУМЕНТАЦИЯ API ---
# Куратор просил убрать Order, Contact и Cart из проекта. 
# Поэтому документация отражает только оставшиеся сущности.
class APIDocsView(APIView):
    """
    Страница-заглушка с актуальной документацией API для дипломной работы.
    Отображает только те роуты, которые остались после очистки проекта.
    """
    def get(self, request, format=None):
        return Response({
            "Документация API": {
                "Авторизация пользователя": {
                    "Регистрация": "/api/register/",
                    "Вход в систему": "/api/login/",
                    "Подтверждение Email": "/api/confirm-email/",
                },
                "Каталог товаров": {
                    "Список всех товаров": "/api/products/",
                    "Список категорий": "/api/categories/",
                    "Список магазинов": "/api/stores/",
                }
            }
        })

# Регистрация страницы документации
urlpatterns += [
    path('docs/', APIDocsView.as_view(), name='manual-docs'),
]

# --- ОТДАЧА МЕДИАФАЙЛОВ ---
# Работает ТОЛЬКО при DEBUG = True (на боевом сервере эту логику берет на себя Nginx/Gunicorn)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)