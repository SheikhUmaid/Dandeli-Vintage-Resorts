
from rest_framework import serializers
from .models import User, OTP, Resort, Room, BookingAttempt, FinalBooking, Payment, RoomImage

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('phone_number', 'name', 'email', 'gender', 'date_of_birth')

class OTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

class ResortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resort
        fields = ('id', 'name', 'location')

class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = ('id', 'image')

class RoomSerializer(serializers.ModelSerializer):
    resort = ResortSerializer()
    images = RoomImageSerializer(many=True, read_only=True)
    class Meta:
        model = Room
        fields = ('id', 'resort', 'room_number', 'capacity', 'images', 'price_per_night')

class BookingAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingAttempt
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class FinalBookingSerializer(serializers.ModelSerializer):
    payment = PaymentSerializer()
    class Meta:
        model = FinalBooking
        fields = '__all__'
