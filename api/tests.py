import os
import sys

# --- БЛОК ИНИЦИАЛИЗАЦИИ DJANGO ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while not os.path.exists(os.path.join(project_root, 'manage.py')) and project_root != '/':
    project_root = os.path.dirname(project_root)

if os.path.exists(os.path.join(project_root, 'manage.py')):
    sys.path.insert(0, project_root)
else:
    raise FileNotFoundError("Файл manage.py не найден.")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diploma_backend.settings')
import django
django.setup()

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from api.models import UserConfirmation, User


class FullUserFlowTest(APITestCase):
    
    def setUp(self):
        self.valid_user_data = {
            'username': 'testuser_flow',
            'email': 'flowtest@example.com',
            'password': 'StrongPass123!'
        }

    def test_01_registration_creates_inactive_user(self):
        response = self.client.post(reverse('register'), self.valid_user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(email=self.valid_user_data['email'])
        conf = UserConfirmation.objects.get(user=user)
        
        self.assertFalse(user.is_active)
        self.assertFalse(conf.is_confirmed)

    def test_02_confirm_email_with_valid_code(self):
        reg_response = self.client.post(reverse('register'), self.valid_user_data, format='json')
        self.assertEqual(reg_response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(email=self.valid_user_data['email'])
        code = user.confirmation.confirmation_code
        
        initial_status = user.is_active
        
        confirm_url = f"{reverse('confirm-email')}?code={code}"
        response = self.client.get(confirm_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], "Email успешно подтвержден!")
        
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertNotEqual(user.is_active, initial_status)

    def test_03_confirm_email_rejects_invalid_code(self):
        self.client.post(reverse('register'), self.valid_user_data, format='json')
        user = User.objects.get(email=self.valid_user_data['email'])
        
        initial_status = user.is_active
        
        response = self.client.get(f"{reverse('confirm-email')}?code=INVALID-CODE")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Неверный код')
        
        user.refresh_from_db()
        self.assertEqual(user.is_active, initial_status)

    def test_04_login_fails_for_unconfirmed_user(self):
        """Система не пускает неподтвержденного пользователя"""
        self.client.post(reverse('register'), self.valid_user_data, format='json')
        
        data = {'username': self.valid_user_data['username'], 'password': self.valid_user_data['password']}
        response = self.client.post(reverse('login'), data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Проверяем реальную ошибку входа из LoginSerializer
        self.assertIn('Ошибка входа', str(response.data))

    def test_05_login_success_for_confirmed_user(self):
        """Полноценный вход в систему после подтверждения почты"""
        self.client.post(reverse('register'), self.valid_user_data, format='json')
        user = User.objects.get(email=self.valid_user_data['email'])
        
        code = user.confirmation.confirmation_code
        self.client.get(f"{reverse('confirm-email')}?code={code}")
        
        data = {'username': self.valid_user_data['username'], 'password': self.valid_user_data['password']}
        response = self.client.post(reverse('login'), data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['msg'], 'OK')

    def test_06_cart_workflow_authenticated(self):
        """Проверка функционала корзины для авторизованного пользователя без использования reverse()"""
        
        # 1. Регистрация
        self.client.post(reverse('register'), self.valid_user_data, format='json')
        user = User.objects.get(email=self.valid_user_data['email'])
        
        # 2. Подтверждение Email
        self.client.get(f"{reverse('confirm-email')}?code={user.confirmation.confirmation_code}")
        
        # 3. Вход (логин). Важно: используем POST, как в вашем views.py
        login_data = {'username': self.valid_user_data['username'], 'password': self.valid_user_data['password']}
        login_response = self.client.post(reverse('login'), login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
    
        cart_url_option_a = '/cart/my_cart/'
        
        response = self.client.get(cart_url_option_a)
        
        if response.status_code == 404:
            cart_url_option_b = '/api/cart/my_cart/'
            response = self.client.get(cart_url_option_b)
            
        if response.status_code == 404:
            resolver_msg = "Маршрут не найден. Доступные варианты: "
            from django.urls import get_resolver
            for name in list(get_resolver().reverse_dict.keys()):
                if isinstance(name, str) and 'cart' in name:
                    resolver_msg += f" [{name}]"
            self.fail(f"404 Not Found. {resolver_msg}")
        
        # Финальная проверка данных
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'NEW')
        self.assertEqual(len(response.data['items']), 0)