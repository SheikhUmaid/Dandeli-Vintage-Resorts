from django.urls import path
from .views import (
    request_otp, 
    verify_otp, 
    UpdateProfileView, 
    RoomSearchView, 
    SelectRoomView, 
    AddGuestDetailsView, 
    CreateRazorpayOrderView,
    VerifyPaymentView
)

urlpatterns = [
    path('auth/otp/request/', request_otp, name='request_otp'),
    path('auth/otp/verify/', verify_otp, name='verify_otp'),
    path('auth/profile/update/', UpdateProfileView.as_view(), name='update_profile'),
    path('rooms/search/', RoomSearchView.as_view(), name='room-search'),
    path('booking/select-rooms/', SelectRoomView.as_view(), name='select-rooms'),
    path('booking/add-guests/', AddGuestDetailsView.as_view(), name='add-guests'),
    path('booking/create-order/', CreateRazorpayOrderView.as_view(), name='create-order'),
    path('booking/verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
]
