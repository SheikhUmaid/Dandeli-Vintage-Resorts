from django.contrib import admin
from .models import (
    User,
    Resort,
    Room,
    BookingAttempt,
    BookingAttemptRooms,
    GuestTemp,
    Payment,
    FinalBooking,
    BookingRoom,
    BookingGuest,
)

admin.site.register(User)
admin.site.register(Resort)
admin.site.register(Room)
admin.site.register(BookingAttempt)
admin.site.register(BookingAttemptRooms)
admin.site.register(GuestTemp)
admin.site.register(Payment)
admin.site.register(FinalBooking)
admin.site.register(BookingRoom)
admin.site.register(BookingGuest)
