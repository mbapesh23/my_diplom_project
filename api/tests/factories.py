# api/tests/factories.py
import factory
from django.contrib.auth.hashers import make_password
from api.models import (
    User, Shop, Category, Product, Contact, Order, 
    OrderItem, ProductInfo, Parameter, ProductParameter,
    UserConfirmation
)


class AnonymousUserFactory(factory.Factory):
    class Meta:
        model = type('AnonymousUser', (), {'is_anonymous': True, 'is_authenticated': False})


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttributeSequence(lambda obj, n: f'user{n}@example.com')
    is_active = False  # Важно для тестов регистрации
    password = factory.PostGenerationMethodCall('set_password', 'password123')

    @factory.post_generation
    def create_confirmation(self, create, extracted, **kwargs):
        if create:
            raw_code = self.password  
            UserConfirmation.objects.create(
                user=self,
                confirmation_code_hash=make_password(raw_code),
                is_confirmed=False
            )


class ShopFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Shop
    user = factory.SubFactory(UserFactory)
    name = factory.Faker('company')


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
    name = factory.Faker('word')


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    name = factory.Faker('bs')


class ProductInfoFactory(factory.django.DjangoModelFactory):
    """Фабрика для связи товара и магазина (именно она нужна тесту корзины)"""
    class Meta:
        model = ProductInfo

    product = factory.SubFactory(ProductFactory)
    shop = factory.SubFactory(ShopFactory)
    price = 1000.00
    quantity = 10  # По умолчанию ставим наличие на складе


class ContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contact
    user = factory.SubFactory(UserFactory)
    name = factory.Faker('name')
    email = factory.Faker('email')


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order
    user = factory.SubFactory(UserFactory)
    status = 'NEW'
    total_amount = 0.00


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem
    order = factory.SubFactory(OrderFactory)
    product_info = factory.SubFactory(ProductInfoFactory)
    quantity = 1
    price_at_order = 1000.00