from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import Shop, Category, Product, Price, Contact, OrderItem, Order, UserConfirmation
from django.db import transaction
from django.contrib.auth.hashers import make_password

UserModel = get_user_model()


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(many=True, queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = '__all__'


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = '__all__'

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = UserModel
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = UserModel(
            username=validated_data['username'],
            email=validated_data['email'],
            password=make_password(validated_data['password']),
            is_active=False 
        )
        
        with transaction.atomic():
            user.save()
            
            from django.utils.crypto import get_random_string
            raw_code = get_random_string(32)
            
            UserConfirmation.objects.create(
                user=user,
                confirmation_code_hash=make_password(raw_code),
                _raw_confirmation_code=raw_code
            )
            
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user or not user.is_active:
            raise serializers.ValidationError("Ошибка входа")
        
        if not hasattr(user, 'confirmation') or not user.confirmation.is_confirmed:
            raise serializers.ValidationError("Подтвердите Email перед входом")
            
        data['user'] = user
        return data


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'

    def validate(self, attrs):
        request_user = self.context.get('request').user
        if Contact.objects.filter(user=request_user, email=attrs.get('email')).exists():
             raise serializers.ValidationError("Контакт с таким Email уже существует")
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'total_amount', 'created_at', 'contact', 'items']


class CartCreateUpdateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all()) 
    quantity = serializers.IntegerField(min_value=1)

#Сериализаторы для сброса кода
class ConfirmEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    confirmation_code = serializers.CharField()