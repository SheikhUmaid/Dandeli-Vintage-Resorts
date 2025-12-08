from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room, Booking, Resort, OTP, User, Coupon
from .serializers import RoomSerializer, BookingSerializer
from django.db.models import Q, Sum
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal

# Request OTP
@api_view(['POST'])
def request_otp(request):
    phone = request.data.get('phone_number')
    if not phone:
        return Response({"error": "Phone number is required"}, status=400)

    otp_code = OTP.generate_otp()
    OTP.objects.create(phone_number=phone, code=otp_code)

    # TODO: integrate SMS API (Twilio, MSG91, etc.)
    
    print(f"🔐 OTP for {phone} is {otp_code}")  # For now: print in console

    return Response({"message": "OTP sent successfully"}, status=200)


# Verify OTP
@api_view(['POST'])
def verify_otp(request):
    phone = request.data.get('phone_number')
    otp = request.data.get('otp')

    if not phone or not otp:
        return Response({"error": "Phone and OTP required"}, status=400)

    try:
        otp_record = OTP.objects.filter(phone_number=phone).latest('created_at')
    except OTP.DoesNotExist:
        return Response({"error": "No OTP found"}, status=404)

    if not otp_record.is_valid():
        return Response({"error": "OTP expired"}, status=400)

    if otp_record.code != otp:
        return Response({"error": "Invalid OTP"}, status=400)

    user, created = User.objects.get_or_create(phone_number=phone)
    refresh = RefreshToken.for_user(user)
    
    is_first_login = created
    response = Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "name": user.name,
            "email": user.email,
            "is_first_login": is_first_login
        }
    }, status=200)

    response.set_cookie(
        key="access_token",
        value=str(refresh.access_token),
        httponly=True,
        secure=True, 
        samesite="Lax"
    )

    return response
    

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        name = request.data.get('name')
        email = request.data.get('email')
        date_of_birth = request.data.get('date_of_birth')
        gender = request.data.get('gender')

        if not name or not email:
            return Response({"error": "Name and email are required"}, status=400)

        user.name = name
        user.email = email
        user.date_of_birth = date_of_birth
        user.gender = gender
        user.save()

        return Response({"message": "Profile updated successfully", "user": {
            "phone_number": user.phone_number,
            "name": user.name,
            "email": user.email,
        }}, status=200)


class RoomSearchView(APIView):
    def get(self, request):
        location = request.query_params.get('location')
        check_in_date_str = request.query_params.get('check_in_date')
        check_out_date_str = request.query_params.get('check_out_date')
        guests_str = request.query_params.get('guests')

        if not all([location, check_in_date_str, check_out_date_str, guests_str]):
            return Response({'error': 'Missing required query parameters.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date()
            guests = int(guests_str)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid date format or guest number.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if guests > 8:
            return Response({'error': 'A maximum of 8 guests are allowed per booking.'}, status=status.HTTP_400_BAD_REQUEST)

        if check_in_date >= check_out_date:
            return Response({'error': 'Check-out date must be after check-in date.'}, status=status.HTTP_400_BAD_REQUEST)

        overlapping_bookings = Booking.objects.filter(
            Q(check_in_date__lt=check_out_date) & Q(check_out_date__gt=check_in_date)
        )
        booked_room_pks = overlapping_bookings.values_list('room__pk', flat=True)

        all_available_rooms = Room.objects.filter(
            resort__address__icontains=location,
            is_available=True
        ).exclude(pk__in=booked_room_pks)

        # First, try to find single rooms that can accommodate the guests
        single_rooms = all_available_rooms.filter(capacity__gte=guests)
        if single_rooms.exists():
            serializer = RoomSerializer(single_rooms, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # If no single room is found, check for resorts that can fit the party
        resort_ids = all_available_rooms.values_list('resort__id', flat=True).distinct()
        multi_room_options = Room.objects.none()

        for resort_id in resort_ids:
            rooms_in_resort = all_available_rooms.filter(resort__id=resort_id)
            total_capacity = rooms_in_resort.aggregate(total=Sum('capacity'))['total'] or 0
            if total_capacity >= guests:
                multi_room_options |= rooms_in_resort
        
        if multi_room_options.exists():
            serializer = RoomSerializer(multi_room_options.distinct(), many=True)
            return Response({
                'message': 'No single room is large enough. You can book multiple rooms at these resorts.',
                'rooms': serializer.data
            }, status=status.HTTP_200_OK)

        return Response([], status=status.HTTP_200_OK)

class BookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a new booking.
        """
        room_id = request.data.get('room_id')
        check_in_date_str = request.data.get('check_in_date')
        check_out_date_str = request.data.get('check_out_date')
        number_of_guests = request.data.get('number_of_guests')
        coupon_code = request.data.get('coupon_code')

        if not all([room_id, check_in_date_str, check_out_date_str, number_of_guests]):
            return Response({'error': 'Missing required fields (room_id, check_in_date, check_out_date, number_of_guests).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room = Room.objects.get(pk=room_id)
            check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date()
            guests = int(number_of_guests)
        except (Room.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Invalid room ID, date format, or guest number.'}, status=status.HTTP_400_BAD_REQUEST)

        if guests > 8:
            return Response({'error': 'A maximum of 8 guests are allowed per booking.'}, status=status.HTTP_400_BAD_REQUEST)

        if check_in_date >= check_out_date:
            return Response({'error': 'Check-out date must be after check-in date.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if guests > room.capacity:
            return Response({'error': f'The selected room can only accomodate {room.capacity} guests.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for overlapping bookings
        overlapping_bookings = Booking.objects.filter(
            room=room,
            check_in_date__lt=check_out_date,
            check_out_date__gt=check_in_date
        )
        if overlapping_bookings.exists():
            return Response({'error': 'This room is not available for the selected dates.'}, status=status.HTTP_409_CONFLICT)

        # Calculate total price
        duration = (check_out_date - check_in_date).days
        total_price = room.price_per_night * duration

        # Handle coupon
        coupon_instance = None
        if coupon_code:
            try:
                coupon_instance = Coupon.objects.get(
                    code=coupon_code,
                    is_active=True,
                    valid_from__lte=timezone.now().date(),
                    valid_to__gte=timezone.now().date()
                )
                discount = (coupon_instance.discount_percentage / Decimal(100)) * total_price
                total_price -= discount
            except Coupon.DoesNotExist:
                return Response({'error': 'Invalid or expired coupon code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create booking
        booking = Booking.objects.create(
            user=request.user,
            room=room,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            number_of_guests=guests,
            total_price=total_price,
            coupon=coupon_instance
        )

        serializer = BookingSerializer(booking)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieve a list of bookings for the current user.
        """
        bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
