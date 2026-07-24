from django.contrib import admin
from .models import (
    User, Shop, Category, Product, Price, Contact, 
    Order, OrderItem, ProductInfo, Parameter, ProductParameter
)

admin.site.register(User)
admin.site.register(Shop)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Price)
admin.site.register(Contact)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ProductInfo)
admin.site.register(Parameter)
admin.site.register(ProductParameter)