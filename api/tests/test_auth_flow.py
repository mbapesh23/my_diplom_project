# api/tests/test_auth_flow.py
import pytest
import urllib.parse # <--- Добавлено для корректного экранирования кода в ссылке
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch
from django.db.models import Sum, F
from api.tests.factories import UserFactory


@pytest.mark.django_db
def test_user_registration_sends_email(api_client):
    data = {
        "username": "testuser",
        "email": "test@example.com", 
        "password": "StrongPass!1"
    }
    
    with patch('django.core.mail.send_mail') as mocked_send:
        response = api_client.post(reverse('register'), data, format='json')
        
    assert response.status_code == status.HTTP_201_CREATED
    assert mocked_send.called
    
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.get(email="test@example.com")
    
    # Проверяем статус из БД (теперь должен быть False благодаря фиксу в сериалайзере)
    assert not user.is_active
    assert hasattr(user, 'confirmation')
    assert user.confirmation.is_confirmed is False


@pytest.mark.django_db
def test_login_fails_if_email_not_confirmed(api_client):
    user = UserFactory() 
    
    data = {"username": user.username, "password": "password123"}
    response = api_client.post(reverse('login'), data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # Ваш LoginSerializer кидает ошибку в non_field_errors
    assert "Ошибка входа" in str(response.data)


@pytest.mark.django_db
def test_confirm_email_vulnerable_to_token_leak(api_client):
    user1 = UserFactory(password='pass_one')
    
    # Берем хэш из созданной фабрией записи подтверждения
    code_hash = user1.confirmation.confirmation_code_hash
    
    # Безопасное формирование URL: спецсимволы ($, /) внутри хэша будут закодированы
    query_string = urllib.parse.urlencode({'code': code_hash})
    url = f"{reverse('confirm-email')}?{query_string}"
    
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    
    user1.refresh_from_db()
    # Уязвимость подтверждается: юзер стал активным просто по GET-запросу с кодом
    assert user1.is_active is True