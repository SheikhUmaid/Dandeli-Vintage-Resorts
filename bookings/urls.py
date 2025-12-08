from django.urls import path
from .views import RoomSearchView, BookingView, request_otp, verify_otp, UpdateProfileView, UserBookingsView

urlpatterns = [
    path('auth/otp/request/', request_otp, name='request_otp'),
    path('auth/otp/verify/', verify_otp, name='verify_otp'),
    path('auth/profile/update/', UpdateProfileView.as_view(), name='update_profile'),
    path('rooms/search/', RoomSearchView.as_view(), name='room-search'),
    path('bookings/create/', BookingView.as_view(), name='booking-create'),
    path('bookings/', UserBookingsView.as_view(), name='user-bookings'),
]
