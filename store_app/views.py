from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from rest_framework import generics
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import *
from .serializers import *
import stripe
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
@api_view(['POST'])
@permission_classes([])
def confirm_order(request):
    try:
        logger.debug("Request data: %s", request.data)
        payment_intent_id = request.data.get('payment_intent_id')
        if not payment_intent_id:
            logger.error("Payment intent ID is missing")
            return Response({'error': 'Payment intent ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the PaymentIntent details from Stripe
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            logger.debug("Payment intent retrieved: %s", payment_intent)
        except stripe.error.StripeError as e:
            logger.error("Stripe error when retrieving PaymentIntent: %s", str(e))
            return Response({'error': 'Failed to retrieve PaymentIntent from Stripe'}, status=status.HTTP_400_BAD_REQUEST)

        # Log the entire payment intent for debugging
        logger.debug("Full payment intent object: %s", payment_intent)

        # Extract details from the payment intent
        total_price = payment_intent.amount_received / 100  # Stripe amount is in cents

        email = None
        if payment_intent.charges and payment_intent.charges.data:
            email = payment_intent.charges.data[0].billing_details.email
        else:
            logger.error("No charges found in payment intent or billing details missing")
            return Response({'error': 'No charges found in payment intent or billing details missing'}, status=status.HTTP_400_BAD_REQUEST)

        items = request.data.get('cart')  # Get cart items from request data
        if not items:
            logger.error("Items metadata is missing")
            return Response({'error': 'Cart items are required'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Create a new order
            user = request.user if request.user.is_authenticated else None
            order = Order.objects.create(
                user=user,
                total_price=total_price,
                payment_intent_id=payment_intent_id  # Ensure this is added
            )

            # Create order items
            for item in items:
                try:
                    product = Product.objects.get(id=item['product_id'])
                except Product.DoesNotExist:
                    logger.error("Product with ID %s not found", item['product_id'])
                    return Response({'error': f'Product with ID {item["product_id"]} not found'}, status=status.HTTP_400_BAD_REQUEST)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=product.price
                )

            order_serialized = OrderSerializer(order)
            logger.debug("Order created successfully: %s", order_serialized.data)
            return Response(order_serialized.data, status=status.HTTP_201_CREATED)
    except stripe.error.StripeError as e:
        logger.error("Stripe error: %s", str(e))
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)





# @csrf_exempt
# @require_POST
@api_view(['POST'])
@permission_classes([])
def create_payment_intent(request):
    print('CREATE PAYMENT INTENT: REQUEST: ', request.data)
    try:
        amount = request.data['amount']
        
        intent = stripe.PaymentIntent.create(
            amount = amount,
            currency = 'usd'
        )
        print ('INTENT >>>>>>>>>>>>', intent)
        return JsonResponse({'clientSecret': intent.client_secret, 'payment_intent': intent.id})
    except Exception as e:
        print('ERROR: ', e)
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([])
def create_confirm_intent(request):
    try:
        response = stripe.PaymentIntent.create(
            confirm=True,
            amount = request.data['amount'],
            currency = 'usd',
            automatic_payment_methods= {'enabled': True},
            confirmation_token=request.data['confirmation_token_id']
        )
        print(response)
        return Response(response)
    except Exception as e:
        print('ERROR: ', e)
        return Response(str(e), status=400)


# Products
@api_view(['GET'])
def get_products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = ProductSerializer(product)
    return Response(serializer.data, status=status.HTTP_200_OK)

# @csrf_exempt
@require_POST
@api_view(['POST'])
@permission_classes([])
def create_user(request):
    required_fields = ['username', 'password', 'email', 'first_name', 'last_name']
    for field in required_fields:
        if field not in request.data:
            return Response({'error': f'{field} is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            user = User.objects.create(
                username=request.data['username']
            )
            user.set_password(request.data['password'])
            user.save()

            profile = Profile.objects.create(
                user=user,
                email=request.data['email'],
                first_name=request.data['first_name'],
                last_name=request.data['last_name']
            )
            profile.save()
        
        profile_serialized = ProfileSerializer(profile)
        return Response(profile_serialized.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    user = request.user
    profile = user.profile
    serializer = ProfileSerializer(profile)
    return Response(serializer.data, status=status.HTTP_200_OK)

# Cart
@api_view(['GET'])
def get_cart(request):
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items = CartProduct.objects.filter(cart=cart)
            items = [
                {
                    'id': item.id,
                    'product': {
                        'id': item.product.id,
                        'name': item.product.name,
                        'price': item.product.price,
                    },
                    'quantity': item.quantity,
                }
                for item in cart_items
            ]
            return JsonResponse({'cart': items})
        except Cart.DoesNotExist:
            return JsonResponse({'cart': []})
    else:
        session_cart = request.session.get('cart', {})
        cart_items = []
        for product_id, quantity in session_cart.items():
            product = Product.objects.get(id=product_id)
            cart_items.append({
                'id': product_id,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': product.price,
                },
                'quantity': quantity,
            })
        return JsonResponse({'cart': cart_items})

@csrf_exempt
@require_POST
def add_to_cart(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        user = request.user
        cart, created = Cart.objects.get_or_create(user=user)
        cart_product, created = CartProduct.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_product.quantity += quantity
        else:
            cart_product.quantity = quantity
        cart_product.save()
        cart_data = {
            'message': 'Item added to cart successfully',
            'cart_product_id': cart_product.id,
            'product': {
                'id': product.id,
                'name': product.name,
                'price': str(product.price),
                'quantity': cart_product.quantity
            }
        }
    else:
        session_cart = request.session.get('cart', {})
        if str(product_id) in session_cart:
            session_cart[str(product_id)]['quantity'] += quantity
        else:
            session_cart[str(product_id)] = {
                'id': product.id,
                'name': product.name,
                'price': str(product.price),
                'quantity': quantity
            }
        request.session['cart'] = session_cart
        request.session.save()
        cart_data = {
            'message': 'Item added to cart successfully',
            'product': session_cart[str(product_id)]
        }

    return JsonResponse(cart_data)


# Order
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders(request):
    orders = Order.objects.filter(user=request.user)
    serializer = OrderSerializer(orders, many=True)
    print(serializer.data)
    return Response(serializer.data, status=status.HTTP_200_OK)
    
   

@csrf_exempt
@require_POST
@api_view(['POST'])
@permission_classes([])
@parser_classes([MultiPartParser, FormParser])
def add_product(request):
    serializer = ProductSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([])
@parser_classes([MultiPartParser, FormParser])
def update_product(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = ProductSerializer(product, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# @api_view(['DELETE'])
# @permission_classes([IsAdminUser])
# def delete_product(request, pk):
#     try:
#         product = Product.objects.get(pk=pk)
#     except Product.DoesNotExist:
#         return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
#     product.delete()
#     return Response(status=status.HTTP_204_NO_CONTENT)


@csrf_exempt
@require_POST
@api_view(['POST'])
@permission_classes([])
def create_guest_order(request):
    required_fields = ['items', 'total_price', 'email']
    for field in required_fields:
        if field not in request.data:
            return Response({'error': f'{field} is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=None,
                total_price=request.data['total_price']
            )

            for item in request.data['items']:
                product = Product.objects.get(id=item['product'])
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=product.price
                )
        
        order_serialized = OrderSerializer(order)
        return Response(order_serialized.data, status=status.HTTP_201_CREATED)
    except Product.DoesNotExist:
        return Response({'error': 'One or more products not found'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ProductImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer

class ProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer

@csrf_exempt
@require_POST
def checkout(request):
    email = request.POST.get('email')
    cart_id = request.POST.get('cart_id')

    if not cart_id:
        return JsonResponse({'error': 'Cart ID is required'}, status=400)

    try:
        cart = Cart.objects.get(id=cart_id)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Cart not found'}, status=404)

    if not cart.cart_products.exists():
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    if request.user.is_authenticated:
        user = request.user
    else:
        user = None

    order = Order.objects.create(user=user, total_price=0)
    total_price = 0

    for cart_product in CartProduct.objects.filter(cart=cart):
        OrderItem.objects.create(
            order=order,
            product=cart_product.product,
            quantity=cart_product.quantity,
            price=cart_product.product.price
        )
        total_price += cart_product.product.price * cart_product.quantity
        cart_product.delete()

    order.total_price = total_price
    order.save()
    cart.delete()

    return JsonResponse({'message': 'Order placed successfully', 'order_id': order.id})

@csrf_exempt
@api_view(['DELETE'])
def delete_cart_item(request, pk):
    print(f"Received CartProduct ID for deletion: {pk}")
    try: 
        cart_product = get_object_or_404(CartProduct, pk=pk)
        cart_product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except CartProduct.DoesNotExist:
        return Response({'error': 'Item not found'})
    


    

@csrf_exempt
@api_view(['POST'])
@permission_classes([])
def create_order(request):
    try:
        data = request.data

        print('received data: ', data)

        total_price = data.get('total_price')
        print('total price: ', total_price)

        payment_intent_id = data.get('payment_intent_id')
        print('payment id', payment_intent_id);

        user = request.user if request.user.is_authenticated else None

        order = Order.objects.create(
            user=user,
            total_price=total_price,
            payment_intent_id=payment_intent_id,
        )
        print('user: ', user)

        for item in data['products']:
            product = get_object_or_404(Product, id=item['product_id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                price=product.price
            )
            print('order items: ', product)

        return JsonResponse({'message': 'Order created successfully'}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
 


@api_view(['GET'])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)
