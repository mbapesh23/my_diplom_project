from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username: str, email: str, password: str, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username: str, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username: str, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    # Добавляем уникальный email и оставляем username как часть учётной записи
    email = models.EmailField(unique=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username


class UserConfirmation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="confirmation")
    confirmation_code_hash = models.CharField(max_length=256)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Confirmation"
        verbose_name_plural = "User Confirmations"

    def __str__(self):
        return f"Confirmation for {self.user.username} - {'confirmed' if self.is_confirmed else 'pending'}"


class Shop(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shops")
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    categories = models.ManyToManyField(Category, related_name="products", blank=True)

    def __str__(self):
        return self.name


class Price(models.Model):
    value = models.DecimalField(max_digits=10, decimal_places=2)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices", null=True, blank=True)

    def __str__(self):
        return f"{self.value} - {self.product.name if self.product else 'no-product'}"


class ProductInfo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="infos")
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="infos")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price_rrc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.IntegerField(default=0)
    model = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.product.name} @ {self.shop.name} - {self.price}"


class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name="parameters")
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name="product_parameters")
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"


class Contact(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contacts")
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.name or self.email} ({self.user.username})"


class Order(models.Model):
    STATUS_CHOICES = [
        ("NEW", "NEW"),
        ("AWAITING_PAYMENT", "AWAITING_PAYMENT"),
        ("PAID", "PAID"),
        ("COMPLETED", "COMPLETED"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name="order_items")
    quantity = models.IntegerField(default=1)
    price_at_order = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_info.product.name} x{self.quantity} for Order #{self.order.id}"