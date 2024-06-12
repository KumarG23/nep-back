from django.contrib import admin
from store_app.models import *


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'email', 'created_at')
    search_fields = ('user__username', 'first_name', 'last_name', 'email')

admin.site.register(Profile, ProfileAdmin)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]

admin.site.register(Product, ProductAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

admin.site.register(Category, CategoryAdmin)


class CartProductInline(admin.TabularInline):
    model = CartProduct
    extra = 1


class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    inlines = [CartProductInline]

admin.site.register(Cart, CartAdmin)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'total_price')
    inlines = [OrderItemInline]

admin.site.register(Order, OrderAdmin)


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username')

admin.site.register(Review, ReviewAdmin)
