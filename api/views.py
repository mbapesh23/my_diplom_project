import logging
from django.db import transaction
from django.db.models import F, Sum
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import login
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings

from .serializers import (
    UserRegisterSerializer, LoginSerializer, ContactSerializer, 
    OrderSerializer, OrderItemSerializer, CartCreateUpdateSerializer,
    ProductSerializer, CategorySerializer, PriceSerializer, StoreSerializer,
    ConfirmEmailSerializer, ConfirmationCodeSerializer, CartSerializer
)
from .models import (
    UserConfirmation, Contact, Order, OrderItem, 
    Product, Category, Shop, ProductInfo
)
from .permissions import IsSupplier

logger = logging.getLogger(__name__)


# --- РЕГИСТРАЦИЯ И ВХОД ---

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        s = UserRegisterSerializer(data=request.data)
        if s.is_valid():
            u = s.save()
            subject = 'Подтверждение регистрации'
            link = f"{settings.FRONTEND_URL}{reverse('confirm-email')}?email={u.email}&code={u.confirmation.confirmation_code}"
            message = f'Для завершения регистрации перейдите по ссылке: {link}'
            
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [u.email])
            except Exception as e:
                logger.error(f"Ошибка отправки почты: {e}")
                
            return Response({"msg": "Проверьте почту"}, status=status.HTTP_201_CREATED)
        
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        s = LoginSerializer(data=request.data)
        if s.is_valid():
            user = s.validated_data['user']
            login(request, user)
            return Response({"msg": "OK"})
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfirmEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        code = request.query_params.get('code')
        try:
            conf = UserConfirmation.objects.select_related('user').get(confirmation_code=code)
            conf.is_confirmed = True
            conf.user.is_active = True
            conf.user.save(update_fields=['is_active'])
            conf.save(update_fields=['is_confirmed'])
            return Response({"detail": "Email успешно подтвержден!"})
        except UserConfirmation.DoesNotExist:
            return Response({'detail': 'Неверный или устаревший код'}, status=status.HTTP_400_BAD_REQUEST)


class ResendConfirmationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        s = ConfirmEmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        
        email = s.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"msg": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
            
        if user.confirmation.is_confirmed:
            return Response({"msg": "Почта уже подтверждена"}, status=status.HTTP_400_BAD_REQUEST)
            
        code = user.confirmation.confirmation_code
        link = f"{settings.FRONTEND_URL}{reverse('confirm-email')}?email={user.email}&code={code}"
        send_mail('Повторное подтверждение', f'Ссылка: {link}', settings.DEFAULT_FROM_EMAIL, [user.email])
        return Response({"msg": "Код отправлен заново"})


# --- КАТАЛОГ ТОВАРОВ ---

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().prefetch_related('categories', 'infos__shop')
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsSupplier]
        return super().get_permissions()

    def get_queryset(self):
        return Shop.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# --- ЛИЧНЫЙ КАБИНЕТ ПОЛЬЗОВАТЕЛЯ ---

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        if self.get_queryset().filter(email=serializer.validated_data['email']).exists():
             from rest_framework.exceptions import ValidationError
             raise ValidationError("Контакт с таким Email уже существует")
        serializer.save(user=self.request.user)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


# --- КОРЗИНА (САМАЯ ВАЖНАЯ ЧАСТЬ) ---

class CartViewSet(viewsets.GenericViewSet):
    """
    ViewSet для корзины. Маршруты прописаны явно в urls.py через @action.
    Это предотвращает конфликты URL и дублирование /cart/.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_cart(self):
        """Приватный метод получения черновика заказа"""
        cart, created = Order.objects.get_or_create(
            user=self.request.user,
            status='NEW',
            defaults={'total_amount': 0}
        )
        return cart

    @action(detail=False, methods=['get'], name='Получить корзину', url_path='my_cart')
    def my_cart(self, request):
        cart = self._get_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], name='Добавить товар', url_path='add_item')
    def add_item(self, request):
        ser = CartCreateUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        product_obj = ser.validated_data['product']
        quantity = int(ser.validated_data['quantity'])
        
        try:
            product_info = ProductInfo.objects.select_related('shop').get(product=product_obj)
        except ProductInfo.DoesNotExist:
            return Response({"detail": "Информация о товаре не найдена"}, status=status.HTTP_404_NOT_FOUND)

        if product_info.quantity_in_stock < quantity:
            return Response({"detail": "Недостаточно товара на складе"}, status=status.HTTP_400_BAD_REQUEST)
            
        cart = self._get_cart()
        
        with transaction.atomic():
            item, created = OrderItem.objects.update_or_create(
                order=cart,
                product_info=product_info,
                defaults={
                    'quantity': quantity,
                    'price_at_order': product_info.price
                }
            )
            
            # Пересчет суммы средствами БД (F-выражения). Защита от race condition.
            new_total = OrderItem.objects.filter(order=cart).aggregate(
                total=Sum(F('price_at_order') * F('quantity'))
            )['total'] or 0
            
            cart.total_amount = new_total
            cart.save(update_fields=['total_amount'])
        
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['delete'], name='Удалить позицию', url_path='remove_item')
    def remove_item(self, request):
        product_info_id = request.query_params.get('product_info_id')
        
        if not product_info_id:
            return Response({"detail": "Укажите product_info_id"}, status=status.HTTP_400_BAD_REQUEST)

        cart = self._get_cart()
        item = get_object_or_404(OrderItem, order=cart, product_info_id=product_info_id)
        
        with transaction.atomic():
            item.delete()
            new_total = OrderItem.objects.filter(order=cart).aggregate(
                total=Sum(F('price_at_order') * F('quantity'))
            )['total'] or 0
            cart.total_amount = new_total
            cart.save(update_fields=['total_amount'])
        
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'], name='Подтвердить заказ', url_path='confirm')
    def confirm(self, request):
        contact_id = request.data.get('contact_id')
        cart = self._get_cart()
        
        if not contact_id:
            return Response({"detail": "Укажите ID контакта"}, status=status.HTTP_400_BAD_REQUEST)
            
        if cart.items.count() == 0:
            return Response({"detail": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)
            
        contact = get_object_or_404(Contact, id=contact_id, user=request.user)
        
        cart.status = 'AWAITING_PAYMENT'
        cart.contact = contact
        cart.save(update_fields=['status', 'contact'])
        
        msg = f"Заказ №{cart.id} подтвержден. Сумма: {cart.total_amount} руб."
        send_mail('Ваш заказ подтвержден', msg, settings.DEFAULT_FROM_EMAIL, [request.user.email])
        
        return Response({"message": "Заказ подтвержден", "order_id": cart.id, "status": cart.status})