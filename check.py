import os
import sys
import django

# Указываем настройки вручную (диплом_бэкенд — это папка вашего проекта из ROOT_URLCONF)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diploma_backend.settings')

# Добавляем корень проекта в пути Python
sys.path.append(os.getcwd())

try:
    django.setup()
except Exception as e:
    print(f"[FATAL] Failed to setup Django: {e}")
    exit(1)

from django.urls import reverse, resolve, NoReverseMatch

print("--- Checking URL /api/cart/my-cart/ ---")
try:
    # Пытаемся найти адрес по имени роута 'cart' и экшена 'my_cart'
    url = reverse('cart-my_cart')
    match = resolve(url)
    
    print("[SUCCESS]")
    print(f"URL matches: {url}")
    print(f"View function: {match.func.__name__}")
    
except NoReverseMatch as e:
    print("[FAILURE] Route not found.")
    print(f"This means your urls.py is wrong or CartViewSet is not registered.")
    print(f"Django says: {e}")
except Exception as e:
    print("[CRITICAL ERROR]")
    print(f"Something crashed in views.py: {e}")