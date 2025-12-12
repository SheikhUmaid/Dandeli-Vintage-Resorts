
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User, OTP, Resort, Room
from unittest.mock import patch

class AuthTests(APITestCase):
    def test_request_otp(self):
        url = reverse('request_otp')
        data = {'phone_number': '1234567890'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'OTP sent successfully')

    def test_verify_otp(self):
        # First, request an OTP
        otp = OTP.objects.create(phone_number='1234567890', code='123456')
        
        url = reverse('verify_otp')
        data = {'phone_number': '1234567890', 'otp': '123456'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

class BookingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number='9876543210')
        self.client.force_authenticate(user=self.user)
        self.resort = Resort.objects.create(name='Test Resort', location='Test Location')
        self.room = Room.objects.create(resort=self.resort, room_number='101', capacity=2, price_per_night=100.00)

    def test_room_search(self):
        url = reverse('room-search')
        response = self.client.get(url, {'resort_id': self.resort.id, 'check_in_date': '2024-06-01', 'check_out_date': '2024-06-03', 'guests': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('booking_attempt_id', response.data)
        self.assertIn('suggested_rooms', response.data)

    def test_select_room(self):
        # Create a booking attempt first
        booking_attempt_url = reverse('room-search')
        response = self.client.get(booking_attempt_url, {'resort_id': self.resort.id, 'check_in_date': '2024-06-01', 'check_out_date': '2024-06-03', 'guests': 2})
        booking_attempt_id = response.data['booking_attempt_id']

        url = reverse('select-rooms')
        data = {'booking_attempt_id': booking_attempt_id, 'room_ids': [self.room.id]}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Rooms selected successfully.')

    def test_add_guests(self):
        # Create a booking attempt and select a room
        booking_attempt_url = reverse('room-search')
        response = self.client.get(booking_attempt_url, {'resort_id': self.resort.id, 'check_in_date': '2024-06-01', 'check_out_date': '2024-06-03', 'guests': 1})
        booking_attempt_id = response.data['booking_attempt_id']
        select_room_url = reverse('select-rooms')
        self.client.post(select_room_url, {'booking_attempt_id': booking_attempt_id, 'room_ids': [self.room.id]}, format='json')

        url = reverse('add-guests')
        data = {'booking_attempt_id': booking_attempt_id, 'guests': [{'room_id': self.room.id, 'name': 'Test Guest', 'age': 30}]}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Guest details added successfully.')

    @patch('razorpay.Client')
    def test_initiate_payment(self, mock_razorpay_client):
        # Mock the razorpay client
        mock_order = {'id': 'order_test', 'amount': 20000, 'currency': 'INR'}
        mock_razorpay_client.return_value.order.create.return_value = mock_order

        # Create a booking attempt, select a room, and add guests
        booking_attempt_url = reverse('room-search')
        response = self.client.get(booking_attempt_url, {'resort_id': self.resort.id, 'check_in_date': '2024-06-01', 'check_out_date': '2024-06-03', 'guests': 1})
        booking_attempt_id = response.data['booking_attempt_id']
        select_room_url = reverse('select-rooms')
        self.client.post(select_room_url, {'booking_attempt_id': booking_attempt_id, 'room_ids': [self.room.id]}, format='json')
        add_guests_url = reverse('add-guests')
        self.client.post(add_guests_url, {'booking_attempt_id': booking_attempt_id, 'guests': [{'room_id': self.room.id, 'name': 'Test Guest', 'age': 30}]}, format='json')

        url = reverse('initiate-payment')
        data = {'booking_attempt_id': booking_attempt_id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Payment initiated.')
        self.assertEqual(response.data['razorpay_order_id'], 'order_test')
