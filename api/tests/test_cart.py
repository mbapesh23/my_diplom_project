# api/tests/test_cart.py
import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch
from django.db.models import Sum, F

from api.tests.factories import UserFactory, ProductInfoFactory


@pytest.mark.django_db
def test_get_empty_cart(api_client):
    """Проверяем создание пустой корзины для нового пользователя"""
    user = UserFactory()
    api_client.force_authenticate(user=user)
    
    url = reverse('cart-my-cart')
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    # DecimalField в DRF по умолчанию возвращает строку '0.00'
    assert response.data['total_amount'] == '0.00' 
    assert response.data['items'] == []


@pytest.mark.django_db
def test_add_item_to_cart_success(api_client):
    """Добавляем товар в корзину и проверяем расчет суммы"""
    user = UserFactory()
    product_info = ProductInfoFactory(price=500.00, quantity=10) 
    
    api_client.force_authenticate(user=user)
    
    url = reverse('cart-add-item')
    data = {
        'product': product_info.product.id,
        'quantity': 3
    }
    
    with patch.object(type(product_info), 'refresh_from_db'):
        response = api_client.post(url, data, format='json')
        
    assert response.status_code == status.HTTP_200_OK
    assert response.data['status'] == 'NEW'
    assert len(response.data['items']) == 1
    
    item_data = response.data['items'][0]
    
    # ИСПРАВЛЕНО: serializer отдает ID напрямую (int), а не вложенный объект
    assert item_data['product_info'] == product_info.product.id
    assert item_data['quantity'] == 3
    assert str(item_data['price_at_order']) == '500.00'
    
    # Проверяем общую сумму корзины
    assert response.data['total_amount'] == '1500.00'
    
    # Проверяем остаток на складе через БД
    product_info.refresh_from_db()
    assert product_info.quantity == 7 # Было 10, купили 3


@pytest.mark.django_db
def test_add_item_insufficient_quantity(api_client):
    """Пытаемся добавить больше товара, чем есть на складе"""
    user = UserFactory()
    product_info = ProductInfoFactory(quantity=2) # На складе всего 2 шт
    
    api_client.force_authenticate(user=user)
    
    url = reverse('cart-add-item')
    data = {'product': product_info.product.id, 'quantity': 5}
    
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Недостаточно товара на складе" in str(response.data)


@pytest.mark.django_db
def test_remove_item_from_cart(api_client):
    """Удаляем позицию из корзины"""
    user = UserFactory()
    pi1 = ProductInfoFactory(price=100.00, quantity=10)
    pi2 = ProductInfoFactory(price=200.00, quantity=10)
    
    api_client.force_authenticate(user=user)
    
    cart_url = reverse('cart-my-cart')
    add_url = reverse('cart-add-item')
    
    # Наполняем корзину
    api_client.post(add_url, {'product': pi1.product.id, 'quantity': 2}, format='json')
    api_client.post(add_url, {'product': pi2.product.id, 'quantity': 1}, format='json')
    
    # Удаляем первую позицию
    remove_url = f"{reverse('cart-remove-item')}?product_info_id={pi1.id}"
    response = api_client.delete(remove_url)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Проверяем состав корзины после удаления
    get_response = api_client.get(cart_url)
    assert len(get_response.data['items']) == 1
    
    remaining_item = get_response.data['items'][0]
    # ИСПРАВЛЕНО: здесь тоже ожидается int (ID), а не dict
    assert remaining_item['product_info'] == pi2.product.id
    assert get_response.data['total_amount'] == '200.00'


@pytest.mark.django_db
def test_confirm_cart_with_contact(api_client):
    """Подтверждаем заказ, переводя его в статус ожидания оплаты"""
    from api.models import Contact, Order  # Добавлен импорт Order для финальной проверки
    
    user = UserFactory()
    pi = ProductInfoFactory(price=1000.00, quantity=5)
    contact = Contact.objects.create(user=user, email="test@example.com")
    
    api_client.force_authenticate(user=user)
    
    add_url = reverse('cart-add-item')
    confirm_url = reverse('cart-confirm')
    
    # Добавляем товар
    api_client.post(add_url, {'product': pi.product.id, 'quantity': 1}, format='json')
    
    # Подтверждаем
    response = api_client.post(confirm_url, {'contact_id': contact.id}, format='json')
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == "Заказ подтвержден"
    
    # Данные корзины находятся внутри ключа 'data'
    order_data = response.data['data']
    
    assert order_data['status'] == 'AWAITING_PAYMENT'
    
    # ИСПРАВЛЕНО: контакт - это int (ID), а не dict
    assert order_data['contact'] == contact.id
    
    # ИСПРАВЛЕНО: id заказа также лежит внутри data, сравниваем с объектом из БД
    confirmed_order = Order.objects.get(user=user, status='AWAITING_PAYMENT')
    assert order_data['id'] == confirmed_order.id