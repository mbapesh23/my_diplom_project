import logging
from django.conf import settings
from django.contrib.auth import login
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.db.models import Sum, F

# Импорт декораторов для настройки документации OpenAPI
from drf_spectacular.utils import extend_schema

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
from .services.check_card_service import CheckCardService

logger = logging.getLogger(__name__)

class RegisterView(APIView):
    """
    Регистрация нового пользователя.
    На указанный Email отправляется ссылка для подтверждения.
    Вход в систему будет возможен только после перехода по ссылке.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=UserRegisterSerializer,
        responses={201: None},
        description="Создает неактивного пользователя и отправляет письмо с кодом."
    )
    def post(self, request) -> Response:
        s = UserRegisterSerializer(data=request.data)
        if s.is_valid():
            u = s.save()
            subject = 'Подтверждение регистрации'
            code_hash = u.confirmation.confirmation_code_hash
            link = f"{settings.FRONTEND_URL}{reverse('confirm-email')}?code={code_hash}"
            message = f'Для завершения регистрации перейдите по ссылке: {link}'
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [u.email])
            except Exception as e:
                logger.error(f"Ошибка отправки почты: {e}")
            return Response({"msg": "Проверьте почту"}, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """
    Авторизация пользователя (получение JWT токенов).
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=LoginSerializer,
        responses={200: None},
        description="Возвращает refresh и access токены при успешном входе."
    )
    def post(self, request) -> Response:
        s = LoginSerializer(data=request.data)
        if s.is_valid():
            user = s.validated_data['user']
            login(request, user)
            refresh = RefreshToken.for_user(user)
            return Response({"refresh": str(refresh), "access": str(refresh.access_token)})
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

class ConfirmEmailView(APIView):
    """
    Подтверждение Email адреса по коду из письма.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        parameters=[ConfirmationCodeSerializer],
        responses={200: None}
    )
    def get(self, request) -> Response:
        code = request.query_params.get('code')
        if not code:
            return Response({'detail': 'Код не передан'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            conf = UserConfirmation.objects.select_related('user').get(confirmation_code_hash=code)
            conf.is_confirmed = True
            conf.user.is_active = True
            conf.user.save(update_fields=['is_active'])
            conf.save(update_fields=['is_confirmed'])
            return Response({"detail": "Email успешно подтвержден!"})
        except UserConfirmation.DoesNotExist:
            return Response({'detail': 'Неверный или устаревший код'}, status=status.HTTP_400_BAD_REQUEST)

class ResendConfirmationView(APIView):
    """
    Повторная отправка кода подтверждения на почту.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=ConfirmEmailSerializer,
        responses={200: None}
    )
    def post(self, request) -> Response:
        s = ConfirmEmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"msg": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
        if user.confirmation.is_confirmed:
            return Response({"msg": "Почта уже подтверждена"}, status=status.HTTP_400_BAD_REQUEST)
        code = user.confirmation.confirmation_code_hash
        link = f"{settings.FRONTEND_URL}{reverse('confirm-email')}?code={code}"
        send_mail('Повторное подтверждение', f'Ссылка: {link}', settings.DEFAULT_FROM_EMAIL, [user.email])
        return Response({"msg": "Код отправлен заново"})

class RequestConfirmationCodeView(APIView):
    """
    Запрашивает новый код подтверждения без создания нового пользователя.
    Нужно, если пользователь удалил письмо с первым кодом.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=ConfirmEmailSerializer,
        responses={200: None}
    )
    def post(self, request) -> Response:
        s = ConfirmEmailSerializer(data=request.data)
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)
            
        email = s.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Не говорим пользователю, что такого Email нет — это мера безопасности
            return Response({"msg": "Если такой адрес существует, код будет отправлен"}, status=status.HTTP_200_OK)

        if hasattr(user, 'confirmation') and user.confirmation.is_confirmed:
            return Response({"msg": "Почта уже подтверждена"}, status=status.HTTP_400_BAD_REQUEST)

        code_hash = user.confirmation.confirmation_code_hash
        link = f"{settings.FRONTEND_URL}{reverse('confirm-email')}?code={code_hash}"
        subject = 'Повторный запрос кода подтверждения'
        message = f'Ваш код подтверждения (или перейдите по ссылке):\n{link}'
        
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        except Exception as e:
            logger.error(f"Ошибка отправки почты при запросе кода: {e}")
            return Response({"detail": "Ошибка сервера отправки"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({"msg": "Проверьте почту"})

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().prefetch_related('categories')
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

class CartViewSet(viewsets.GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def _get_cart(self):
        cart, created = Order.objects.get_or_create(
            user=self.request.user,
            status='NEW',
            defaults={'total_amount': 0}
        )
        return cart

    @extend_schema(
        responses={200: CartSerializer},
        description="Получение текущей корзины пользователя."
    )
    @action(detail=False, methods=['get'], name='Получить корзину', url_path='my_cart')
    def my_cart(self, request) -> Response:
        cart = self._get_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @extend_schema(
        request=CartCreateUpdateSerializer,
        responses={200: CartSerializer},
        description="Добавление товара в корзину."
    )
    @action(detail=False, methods=['post'], name='Добавить товар', url_path='add_item')
    def add_item(self, request) -> Response:
        ser = CartCreateUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        product_obj = ser.validated_data['product']
        quantity = int(ser.validated_data['quantity'])
        
        try:
            product_info = ProductInfo.objects.select_for_update().select_related('shop').get(product=product_obj)
        except ProductInfo.DoesNotExist:
            return Response({"detail": "Информация о товаре не найдена"}, status=status.HTTP_404_NOT_FOUND)

        if product_info.quantity < quantity:
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

            product_info.quantity -= quantity
            product_info.save(update_fields=['quantity'])
            
            new_total = OrderItem.objects.filter(order=cart).aggregate(
                total=Sum(F('price_at_order') * F('quantity'))
            )['total'] or 0
            
            cart.total_amount = new_total
            cart.save(update_fields=['total_amount'])
        
        return Response(CartSerializer(cart).data)

    @extend_schema(
        parameters=[
            # Описываем query параметр id позиции
            {'in': 'query', 'name': 'product_info_id', 'type': 'integer', 'required': True}
        ],
        responses={204: None},
        description="Удаление позиции из корзины."
    )
    @action(detail=False, methods=['delete'], name='Удалить позицию', url_path='remove_item')
    def remove_item(self, request) -> Response:
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
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=ContactSerializer(many=False),
        responses={200: CartSerializer},
        description="Подтверждение заказа с привязкой контакта."
    )
    @action(detail=False, methods=['post'], name='Подтвердить заказ', url_path='confirm')
    def confirm(self, request) -> Response:
        contact_id = request.data.get('contact_id')
        cart = self._get_cart()
        
        if cart.status != 'NEW':
            return Response({"detail": f"Заказ имеет статус {cart.status}"}, status=status.HTTP_400_BAD_REQUEST)

        if not contact_id:
            return Response({"detail": "Укажите ID контакта"}, status=status.HTTP_400_BAD_REQUEST)
            
        if cart.items.count() == 0:
            return Response({"detail": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)
            
        contact = get_object_or_404(Contact, id=contact_id, user=request.user)
        
        with transaction.atomic():
            cart.status = 'AWAITING_PAYMENT'
            cart.contact = contact
            cart.save(update_fields=['status', 'contact', 'total_amount'])
        
        msg = f"Заказ №{cart.id} подтвержден. Сумма: {cart.total_amount} руб."
        send_mail('Ваш заказ подтвержден', msg, settings.DEFAULT_FROM_EMAIL, [request.user.email])

        serializer = self.get_serializer(cart)
        
        return Response({
            "message": "Заказ подтвержден",
            "data": serializer.data
        })