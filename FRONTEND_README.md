# Frontend Documentation for Django Resort Booking API

This document provides the necessary information for a frontend developer to interact with the Django Resort Booking API. The API handles user authentication, profile management, and a multi-step booking process.

## Getting Started

### Base URL

The API is running at `http://localhost:8000/api/`.

### Authentication

The API uses JWT for authentication. The workflow is as follows:

1.  The user provides a phone number.
2.  The backend sends an OTP to that number.
3.  The user submits the phone number and OTP to the verify endpoint.
4.  The backend responds with an access and refresh token.

All subsequent authenticated requests must include the access token in the `Authorization` header as a Bearer token:

`Authorization: Bearer <your_access_token>`

## API Endpoints

### Authentication

#### `POST /auth/otp/request/`

Initiates the login or registration process by sending an OTP to the user's phone number.

**Request Body:**
```json
{
    "phone_number": "9999988888"
}
```

#### `POST /auth/otp/verify/`

Verifies the OTP and, if valid, returns JWT access and refresh tokens. A new user is created if one doesn't already exist.

**Request Body:**
```json
{
    "phone_number": "9999988888",
    "otp": "123456"
}
```

### Profile Management

#### `POST /auth/profile/update/`

Allows an authenticated user to update their profile information.

**Request Body:**
```json
{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "date_of_birth": "1990-01-15",
    "gender": "Male"
}
```

### Booking Flow

The booking process is a sequence of API calls.

#### 1. `GET /rooms/search/`

Searches for available rooms based on location, dates, and number of guests.

**Query Parameters:**
-   `location`: The desired location (e.g., "Goa").
-   `check_in_date`: Format `YYYY-MM-DD`.
-   `check_out_date`: Format `YYYY-MM-DD`.
-   `guests`: The total number of guests.

**Response:**
A list of resorts matching the criteria, each with a list of available rooms.
```json
[
    {
        "resort_id": 1,
        "resort_name": "Beachside Resort",
        "location": "Goa",
        "available_rooms": [
            {
                "id": 101,
                "room_number": "A101",
                "capacity": 2,
                "price_per_night": "7500.00",
                "images": [
                    {
                        "image": "/media/room_images/beach_view.jpg"
                    }
                ]
            },
            {
                "id": 102,
                "room_number": "A102",
                "capacity": 4,
                "price_per_night": "12000.00",
                "images": []
            }
        ]
    }
]
```

#### 2. `POST /booking/select-rooms/`

Creates a `BookingAttempt` and locks in the rooms the user has chosen. This is the first step that requires user authentication in the booking flow.

**Request Body:**
```json
{
    "resort_id": 1,
    "room_ids": [101, 102],
    "check_in_date": "2024-12-20",
    "check_out_date": "2024-12-25",
    "guests": 6
}
```

**Response:**
```json
{
    "message": "Rooms selected successfully. Proceed to add guest details.",
    "booking_attempt_id": 123
}
```

#### 3. `POST /booking/add-guests/`

Adds the details for each guest to the booking attempt.

**Request Body:**
```json
{
    "booking_attempt_id": 123,
    "guests": [
        {"room_id": 101, "name": "Alice", "age": 30},
        {"room_id": 101, "name": "Bob", "age": 32},
        {"room_id": 102, "name": "Charlie", "age": 10},
        {"room_id": 102, "name": "Diana", "age": 12},
        {"room_id": 102, "name": "Eve", "age": 5},
        {"room_id": 102, "name": "Frank", "age": 6}
    ]
}
```

#### 4. `POST /booking/initiate-payment/`

Calculates the total price and creates a Razorpay order.

**Request Body:**
```json
{
    "booking_attempt_id": 123
}
```

**Response:**
```json
{
    "message": "Payment initiated.",
    "payment_id": 45,
    "razorpay_order_id": "order_XXXXXXXXXXXXXX",
    "razorpay_key": "rzp_test_XXXXXXXXXXXXXX",
    "amount": 287500.00
}
```
The frontend should use the `razorpay_order_id` and `razorpay_key` to open the Razorpay payment dialog.

#### 5. Payment Confirmation

Payment confirmation is handled via a backend webhook. The frontend does not need to call a specific endpoint for this. Once the user completes the Razorpay payment, the backend will automatically confirm the booking.
