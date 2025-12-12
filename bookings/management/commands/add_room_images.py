
import os
from django.core.management.base import BaseCommand
from django.core.files import File
from PIL import Image
from io import BytesIO

from bookings.models import Room, RoomImage

class Command(BaseCommand):
    help = 'Adds sample images to rooms'

    def handle(self, *args, **kwargs):
        # Create a dummy image
        im = Image.new(mode="RGB", size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        # Get all rooms
        rooms = Room.objects.all()

        if not rooms:
            self.stdout.write(self.style.WARNING('No rooms found in the database.'))
            return

        for room in rooms:
            # Create a RoomImage
            room_image = RoomImage(room=room)
            room_image.image.save(f'room_{room.id}_sample.jpg', File(im_io))
            room_image.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully added image to room {room.room_number}'))
