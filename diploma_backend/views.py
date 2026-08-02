from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

def index(request):
    return HttpResponse("<h1>Главная страница дипломного проекта</h1>")

def partner_update(request):
    # Заглушка — можно заменить реальной логикой обновления партнёра
    return JsonResponse({"status": "ok", "message": "PartnerUpdate placeholder"})

def docs(request):
    """
    Простой endpoint для вывода документации API.
    Можно заменить на динамическое формирование списка маршрутов.
    """
    endpoints = [
        {"path": "/docs/", "methods": ["GET"], "description": "Документация API"},
        {"path": "/register/", "methods": ["POST"], "description": "Регистрация пользователя"},
        {"path": "/login/", "methods": ["POST"], "description": "Авторизация"},
        {"path": "/api/products/", "methods": ["GET"], "description": "Список продуктов"},
        {"path": "/docs/", "methods": ["GET"], "description": "Документация API (дубликат)"},
    ]
    return JsonResponse(endpoints, safe=False)