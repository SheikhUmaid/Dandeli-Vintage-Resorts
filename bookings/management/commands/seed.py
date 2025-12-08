from django.core.management.base import BaseCommand
from bookings.models import Resort, RoomType, Room, User, Booking, Payment
from decimal import Decimal
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Seeds the database with initial data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Clean up existing data to avoid duplicates
        Payment.objects.all().delete()
        Booking.objects.all().delete()
        Room.objects.all().delete()
        RoomType.objects.all().delete()
        Resort.objects.all().delete()

        # Create a resort
        resort = Resort.objects.create(
            name="Gemini's Paradise",
            address="123 AI Lane, Tech City",
            description="A beautiful resort powered by Gemini.",
            contact_number="123-456-7890",
            email="contact@geminisparadise.com"
        )
        self.stdout.write(self.style.SUCCESS(f'Successfully created resort: {resort.name}'))

        # Create room types
        deluxe_room_type = RoomType.objects.create(resort=resort, name="Deluxe Room", description="A spacious room with a king-sized bed.")
        suite_room_type = RoomType.objects.create(resort=resort, name="Suite", description="A luxurious suite with a separate living area.")
        self.stdout.write(self.style.SUCCESS('Successfully created room types'))

        # Create rooms
        for i in range(1, 6):
            Room.objects.create(
                resort=resort,
                room_number=f'D{i}',
                room_type=deluxe_room_type,
                price_per_night=Decimal('150.00'),
                capacity=2,
            )
        for i in range(1, 4):
            Room.objects.create(
                resort=resort,
                room_number=f'S{i}',
                room_type=suite_room_type,
                price_per_night=Decimal('250.00'),
                capacity=4,
            )
        self.stdout.write(self.style.SUCCESS('Successfully created rooms'))
        
        # Create Bookings and Payments if a user exists
        if User.objects.exists():
            user = User.objects.first()
            room_to_book = Room.objects.first()

            booking = Booking.objects.create(
                user=user,
                room=room_to_book,
                check_in_date=date.today() + timedelta(days=10),
                check_out_date=date.today() + timedelta(days=15),
                number_of_guests=2,
                total_price=room_to_book.price_per_night * 5,
                booking_status='Confirmed'
            )

            Payment.objects.create(
                booking=booking,
                payment_method='Credit Card',
                payment_status='Completed'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created a booking and a payment.'))
        else:
            self.stdout.write(self.style.WARNING('No users found in the database. Skipping creation of bookings and payments.'))


        self.stdout.write(self.style.SUCCESS('Database seeding complete!'))
