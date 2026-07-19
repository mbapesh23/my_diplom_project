from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import login
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
# ИСПРАВЛЕНИЕ PEP8: явный импорт вместо wildcard
from .models import (
    UserConfirmation, Contact, Order, OrderItem, 
    Product, Category, Shop, ProductInfo
)
from .serializers import (
    UserRegisterSerializer, LoginSerializer, ContactSerializer, 
    OrderSerializer, OrderItemSerializer, CartCreateUpdateSerializer,
    ProductSerializer, CategorySerializer, PriceSerializer, StoreSerializer,
    ConfirmEmailSerializer, ConfirmationCodeSerializer, CartSerializer
)
from django.db.models import Sum


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
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [u.email])
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
            conf.user.save()
            conf.save()
            return Response({"detail": "Email успешно подтвержден!"})
        except UserConfirmation.DoesNotExist:
            return Response({'detail': 'Неверный код'}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({"msg": "Уже подтверждено"}, status=status.HTTP_400_BAD_REQUEST)
            
        code = user.confirmation.confirmation_code
        link = f"{settings.FRONTEND_URL}{reverse('confirm-email')}?email={user.email}&code={code}"
        send_mail('Повторное подтверждение', f'Ссылка: {link}', settings.DEFAULT_FROM_EMAIL, [user.email])
        return Response({"msg": "Код отправлен заново"})


# --- КАТАЛОГ ---

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().prefetch_related('categories', 'shop__prices') # поправлен путь для prefetch
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Shop.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]


# --- ЛИЧНЫЙ КАБИНЕТ ПОЛЬЗОВАТЕЛЯ ---

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        if self.get_queryset().filter(email=serializer.validated_data['email']).exists():
             raise ValidationError("Контакт с таким Email уже существует")
        serializer.save(user=self.request.user)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


# --- КОРЗИНА (ИСПРАВЛЕННАЯ) ---

class CartViewSet(viewsets.GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_cart(self):
        cart, _ = Order.objects.get_or_create(
            user=self.request.user,
            status='NEW',
            defaults={'total_amount': 0}
        )
        return cart

    @action(detail=False, methods=['get'], name='cart_my_cart', url_path='my_cart')
    def my_cart(self, request):
        cart = self.get_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], name='cart_add_item', url_path='add_item')
    def add_item(self, request):
        ser = CartCreateUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        
        product_obj = ser.validated_data['product']
        quantity = ser.validated_data['quantity']
        
        try:
            product_info = ProductInfo.objects.select_related('store').get(product=product_obj)
        except ProductInfo.DoesNotExist:
            return Response({"detail": "Информация о товаре не найдена"}, status=status.HTTP_404_NOT_FOUND)

        if product_info.quantity_in_stock < int(quantity):
            return Response({"detail": "Недостаточно товара на складе"}, status=status.HTTP_400_BAD_REQUEST)
            
        cart = self.get_cart()
        
        item, created = OrderItem.objects.update_or_create(
            order=cart,
            product_info=product_info,
            defaults={
                'quantity': int(quantity),
                'price_at_order': product_info.price
            }
        )
        
        total = cart.items.aggregate(total_sum=Sum('price_at_order__sum'))['total_sum'] 
        cart.total_amount = sum(item.quantity * item.price_at_order for item in cart.items.all())
        cart.save(update_fields=['total_amount'])
        
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['delete'], name='cart_remove_item', url_path='remove_item')
    def remove_item(self, request):
        #Используем ID информации о товаре
        product_info_id = request.query_params.get('product_info_id')
        
        if not product_info_id:
            return Response({"detail": "Укажите product_info_id"}, status=status.HTTP_400_BAD_REQUEST)

        cart = self.get_cart()
        item = get_object_or_404(OrderItem, order=cart, product_info_id=product_info_id)
        item.delete()
        
        cart.total_amount = sum(item.quantity * item.price_at_order for item in cart.items.all())
        cart.save(update_fields=['total_amount'])
        
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'], name='cart_confirm', url_path='confirm')
    def confirm(self, request):
        contact_id = request.data.get('contact_id')
        cart = self.get_cart()
        
        if not contact_id:
            return Response({"detail": "Укажите ID контакта"}, status=status.HTTP_400_BAD_REQUEST)
            
        if cart.items.count() == 0:
            return Response({"detail": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)
            
        contact = get_object_or_404(Contact, id=contact_id, user=request.user)
        
        cart.status = 'AWAITING_PAYMENT'
        cart.contact = contact
        cart.save()
        
        msg = f"Заказ №{cart.id} ожидает оплаты. Сумма: {cart.total_amount} руб."
        send_mail('Ваш заказ подтвержден', msg, settings.DEFAULT_FROM_EMAIL, [request.user.email])
        
        return Response({"message": "Заказ подтвержден", "order_id": cart.id, "status": cart.status})