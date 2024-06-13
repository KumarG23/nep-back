"""
URL configuration for nepali_store_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView
from store_app.views import *
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('products/', get_products, name='get_products'),
    path('products/<int:pk>/', get_product_detail, name='get_product_detail'),
    path('user/create/', create_user, name='create_user'),
    path('profiles/me/', get_profile, name='get_profile'),
    path('cart/', get_cart, name='get_cart'),
    path('cart/add/', add_to_cart, name='add_to_cart'),
    path('orders/', create_order, name='create_order'),
    path('orders/get', get_orders, name='get_orders'),
    path('admin/products/add/', add_product, name='add_product'),
    path('admin/products/<int:pk>/update/', update_product, name='update_product'),
    path('admin/products/<int:pk>/delete/', delete_product, name='delete_product'),
    path('orders/guest/', create_guest_order, name='create_guest_order'),
    path('product-images/', ProductImageListCreateView.as_view(), name='product_image_list_create'),
    path('product-images/<int:pk>/', ProductImageDetailView.as_view(), name='product_image_detail'),
    path('checkout/', checkout, name='checkout'),
    path('create-payment-intent/', create_payment_intent, name='create-payment-intent'),
    path('cart/<int:pk>/delete/', delete_cart_item, name='delete_cart_item'),
    path('orders/confirm', confirm_order, name='confirm_order')
    # path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    # path('order/success/', order_success, name='order_success'),

]
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
