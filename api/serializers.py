from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Car, Inquiry, Order

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'phone', 'location', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            role=validated_data.get('role', 'buyer'),
            phone=validated_data.get('phone', ''),
            location=validated_data.get('location', 'Ahmedabad'),
            password=validated_data['password']
        )
        return user

class CarSerializer(serializers.ModelSerializer):
    seller_username = serializers.CharField(source='seller.username', read_only=True)
    seller_phone = serializers.CharField(source='seller.phone', read_only=True)

    class Meta:
        model = Car
        fields = '__all__'
        read_only_fields = ('seller', 'created_at')

class InquirySerializer(serializers.ModelSerializer):
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)
    car_name = serializers.CharField(source='car.name', read_only=True)
    car_price = serializers.FloatField(source='car.price', read_only=True)
    car_image = serializers.CharField(source='car.image', read_only=True)
    seller_username = serializers.CharField(source='car.seller.username', read_only=True)

    class Meta:
        model = Inquiry
        fields = '__all__'
        read_only_fields = ('buyer', 'created_at')

class OrderSerializer(serializers.ModelSerializer):
    buyer_username = serializers.CharField(source='buyer.username', read_only=True)
    car_name = serializers.CharField(source='car.name', read_only=True)
    car_image = serializers.CharField(source='car.image', read_only=True)
    car_seller_username = serializers.CharField(source='car.seller.username', read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('buyer', 'created_at')
