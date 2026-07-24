from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('Пользователь должен иметь имя')
        if not email:
            raise ValueError('Пользователь должен иметь Email')
        
        email = self.normalize_email(email)
        
        extra_fields.setdefault('is_active', False) 
        
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True) 
        return self.create_user(username, email, password, **extra_fields)

class UserConfirmation(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='confirmation')
    confirmation_code = models.CharField(max_length=64, unique=True)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class User(AbstractUser):
    email = models.EmailField('Email адрес', unique=True)
    objects = UserManager()
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

class Shop(models.Model):
    name = models.CharField(max_length=255)
    url_or_file_path = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shops', null=True, blank=True)

class Category(models.Model):
    name = models.CharField(max_length=255)

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    supplier = models.CharField(max_length=255, blank=True)
    categories = models.ManyToManyField(Category, related_name='products', blank=True)

class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices')
    store = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_in_stock = models.IntegerField()

class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    last_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=255, blank=True)
    street = models.CharField(max_length=255, blank=True)
    house = models.CharField(max_length=50, blank=True)
    building = models.CharField(max_length=50, blank=True)
    structure = models.CharField(max_length=50, blank=True)
    apartment = models.CharField(max_length=50, blank=True)

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)
    status_choices = [
        ('NEW', 'Новый'),
        ('IN_PROGRESS', 'В обработке'),
        ('SHIPPED', 'Отправлен'),
        ('DELIVERED', 'Доставлен'),
        ('CANCELLED', 'Отменен'),
        ('AWAITING_PAYMENT', 'Ожидает оплаты'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='NEW')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class Parameter(models.Model):
    name = models.CharField(max_length=255)

class ProductParameter(models.Model):
    product_info = models.ForeignKey('ProductInfo', on_delete=models.CASCADE, related_name='parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name='product_parameters')
    value = models.CharField(max_length=255)

class ProductInfo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='infos')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='product_infos')
    external_id = models.CharField(max_length=255, unique=True) 
    model = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price_rrc = models.DecimalField("Рекомендуемая розничная цена", max_digits=10, decimal_places=2)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name='order_items')
    store = models.ForeignKey(Shop, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)

@receiver(post_save, sender=User)
def create_confirmation_on_user_create(sender, instance, created, **kwargs):
    if created and not instance.is_staff:
        code = get_random_string(32)
        UserConfirmation.objects.create(user=instance, confirmation_code=code)