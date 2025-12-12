
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room, Resort, OTP, User, BookingAttempt, BookingAttemptRooms, GuestTemp, Payment, FinalBooking, BookingRoom, BookingGuest
from .serializers import RoomSerializer
from django.db.models import Q, Sum
from datetime import datetime, timedelta
from rest_framework.decorators import api_view
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json

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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        location = request.query_params.get('location')
        check_in_date_str = request.query_params.get('check_in_date')
        check_out_date_str = request.query_params.get('check_out_date')
        guests_str = request.query_params.get('guests')

        if not all([location, check_in_date_str, check_out_date_str, guests_str]):
            return Response({'error': 'Missing required query parameters (location, check_in_date, check_out_date, guests).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date()
            guests = int(guests_str)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid date format or guest number.'}, status=status.HTTP_400_BAD_REQUEST)

        if check_in_date >= check_out_date:
            return Response({'error': 'Check-out date must be after check-in date.'}, status=status.HTTP_400_BAD_REQUEST)

        resorts = Resort.objects.filter(location__icontains=location)
        if not resorts.exists():
            return Response({'message': 'No resorts found in the specified location.'}, status=status.HTTP_404_NOT_FOUND)

        results = []
        for resort in resorts:
            overlapping_bookings = FinalBooking.objects.filter(
                resort=resort,
                check_in__lt=check_out_date,
                check_out__gt=check_in_date,
                status='confirmed'
            )
            booked_room_pks = BookingRoom.objects.filter(booking__in=overlapping_bookings).values_list('room__pk', flat=True)

            available_rooms = Room.objects.filter(resort=resort).exclude(pk__in=booked_room_pks)
            
            total_capacity = available_rooms.aggregate(total_capacity=Sum('capacity'))['total_capacity'] or 0
            
            if total_capacity >= guests:
                resort_data = {
                    'resort_id': resort.id,
                    'resort_name': resort.name,
                    'location': resort.location,
                    'available_rooms': RoomSerializer(available_rooms, many=True).data
                }
                results.append(resort_data)

        if not results:
             return Response({'message': 'No rooms available for the selected criteria in this location.'}, status=status.HTTP_200_OK)

        return Response(results, status=status.HTTP_200_OK)

class SelectRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        resort_id = request.data.get('resort_id')
        room_ids = request.data.get('room_ids')
        check_in_date_str = request.data.get('check_in_date')
        check_out_date_str = request.data.get('check_out_date')
        guests_str = request.data.get('guests')

        if not all([resort_id, room_ids, check_in_date_str, check_out_date_str, guests_str]):
            return Response({'error': 'Missing required fields (resort_id, room_ids, check_in_date, check_out_date, guests).'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resort = Resort.objects.get(pk=resort_id)
            check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date()
            guests = int(guests_str)
            rooms = Room.objects.filter(pk__in=room_ids, resort=resort)
        except (Resort.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Invalid resort ID, date format or guest number.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if len(room_ids) != rooms.count():
            return Response({'error': 'Some selected rooms do not belong to the specified resort.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate room selection
        total_capacity = rooms.aggregate(Sum('capacity'))['capacity__sum'] or 0
        if total_capacity < guests:
            return Response({'error': 'The selected rooms do not have enough capacity for all guests.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Verify rooms are actually available
        overlapping_bookings = FinalBooking.objects.filter(
            resort=resort,
            check_in__lt=check_out_date,
            check_out__gt=check_in_date,
            status='confirmed'
        )
        booked_room_pks = BookingRoom.objects.filter(booking__in=overlapping_bookings).values_list('room__pk', flat=True)
        
        for room_id in room_ids:
            if room_id in booked_room_pks:
                return Response({'error': f'Room with id {room_id} is not available for the selected dates.'}, status=status.HTTP_400_BAD_REQUEST)


        # Create a booking attempt
        booking_attempt = BookingAttempt.objects.create(
            user=request.user,
            resort=resort,
            check_in=check_in_date,
            check_out=check_out_date,
            guest_count=guests,
            expires_at=timezone.now() + timedelta(minutes=30)
        )

        for room in rooms:
            BookingAttemptRooms.objects.create(attempt=booking_attempt, room=room)

        return Response({
            'message': 'Rooms selected successfully. Proceed to add guest details.',
            'booking_attempt_id': booking_attempt.id
        }, status=status.HTTP_200_OK)

class AddGuestDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_attempt_id = request.data.get('booking_attempt_id')
        guests = request.data.get('guests') # List of guest details

        if not booking_attempt_id or not guests:
            return Response({'error': 'Booking attempt ID and guest details are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking_attempt = BookingAttempt.objects.get(pk=booking_attempt_id, user=request.user)
        except BookingAttempt.DoesNotExist:
            return Response({'error': 'Invalid booking attempt ID.'}, status=status.HTTP_404_NOT_FOUND)

        for guest_data in guests:
            GuestTemp.objects.create(
                attempt=booking_attempt,
                room_id=guest_data['room_id'],
                name=guest_data['name'],
                age=guest_data['age']
            )

        return Response({'message': 'Guest details added successfully.'}, status=status.HTTP_200_OK)

class CreateRazorpayOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_attempt_id = request.data.get("booking_attempt_id")

        if not booking_attempt_id:
            return Response({"error": "Missing booking_attempt_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking_attempt = BookingAttempt.objects.get(pk=booking_attempt_id, user=request.user)
        except BookingAttempt.DoesNotExist:
            return Response({"error": "Invalid booking_attempt_id"}, status=status.HTTP_404_NOT_FOUND)

        # Calculate total amount
        total_price = 0
        attempt_rooms = BookingAttemptRooms.objects.filter(attempt=booking_attempt)
        duration = (booking_attempt.check_out - booking_attempt.check_in).days
        for attempt_room in attempt_rooms:
            total_price += attempt_room.room.price_per_night * duration
        
        if total_price <= 0:
            return Response({"error": "Calculated amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # Razorpay expects amount in paise
        razorpay_order = client.order.create({
            "amount": int(total_price) * 100,
            "currency": "INR",
            "receipt": f"booking_{booking_attempt.id}",
            "payment_capture": 1
        })

        # Create a payment record
        payment = Payment.objects.create(
            attempt=booking_attempt,
            amount=total_price,
            provider="Razorpay",
            provider_payment_id=razorpay_order["id"], # Store Razorpay Order ID
            status="initiated",
        )

        return Response({
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": "INR",
            "key": settings.RAZORPAY_KEY_ID,
            "booking_attempt_id": booking_attempt.id,
            "payment_id": payment.id
        }, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        order_id = data.get("razorpay_order_id")
        payment_id = data.get("razorpay_payment_id")
        signature = data.get("razorpay_signature")

        if not all([order_id, payment_id, signature]):
            return Response(
                {"error": "Incomplete payment data."},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        params_dict = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        try:
            # Verify signature
            client.utility.verify_payment_signature(params_dict)

            # Fetch and update payment & booking
            payment = Payment.objects.filter(provider_payment_id=order_id).first()
            if not payment:
                return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if booking attempt belongs to the user
            booking_attempt = payment.attempt
            if booking_attempt.user != request.user:
                 return Response({"error": "Booking does not belong to the authenticated user."}, status=status.HTTP_403_FORBIDDEN)

            payment.status = 'success'
            payment.save()
            
            # Finalize the booking
            final_booking = FinalBooking.objects.create(
                user=booking_attempt.user,
                resort=booking_attempt.resort,
                check_in=booking_attempt.check_in,
                check_out=booking_attempt.check_out,
                status='confirmed',
                payment=payment
            )

            for attempt_room in BookingAttemptRooms.objects.filter(attempt=booking_attempt):
                BookingRoom.objects.create(booking=final_booking, room=attempt_room.room)
            
            for guest_temp in GuestTemp.objects.filter(attempt=booking_attempt):
                BookingGuest.objects.create(
                    booking=final_booking,
                    room=guest_temp.room,
                    name=guest_temp.name,
                    age=guest_temp.age
                )

            booking_attempt.status = 'completed'
            booking_attempt.save()

            # TODO: Add a task to send booking confirmation emails
            # send_booking_emails_task.delay(final_booking.id)

            return Response({
                "success": True,
                "message": "Payment verified successfully",
                "booking_id": final_booking.id
            })

        except razorpay.errors.SignatureVerificationError:
            return Response(
                {"success": False, "message": "Payment verification failed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Generic error for any other issues
            return Response(
                {"success": False, "message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
