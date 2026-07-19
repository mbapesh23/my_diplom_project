from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'stores', views.StoreViewSet)
router.register(r'contacts', views.ContactViewSet, basename='contact')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'cart', views.CartViewSet, basename='cart')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('confirm-email/', views.ConfirmEmailView.as_view(), name='confirm-email'),
    path('resend-confirmation/', views.ResendConfirmationView.as_view(), name='resend_confirm'),
]