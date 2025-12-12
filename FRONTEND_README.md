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
            }
        ]
    }
]
```

#### 2. `POST /booking/select-rooms/`

Creates a `BookingAttempt` and locks in the rooms the user has chosen.

**Request Body:**
```json
{
    "resort_id": 1,
    "room_ids": [101],
    "check_in_date": "2024-12-20",
    "check_out_date": "2024-12-25",
    "guests": 2
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
        {"room_id": 101, "name": "Bob", "age": 32}
    ]
}
```

#### 4. `POST /booking/create-order/`

Calculates the total price for the booking attempt and creates a Razorpay order.

**Request Body:**
```json
{
    "booking_attempt_id": 123
}
```

**Response:**
The frontend should use these details to open the Razorpay payment dialog.
```json
{
    "order_id": "order_XXXXXXXXXXXXXX",
    "amount": 3750000, 
    "currency": "INR",
    "key": "rzp_test_XXXXXXXXXXXXXX",
    "booking_attempt_id": 123,
    "payment_id": 45
}
```

#### 5. `POST /booking/verify-payment/`

After the user completes the payment in the Razorpay dialog, the frontend must call this endpoint to verify the payment with the backend.

**Request Body:**
```json
{
    "razorpay_order_id": "order_XXXXXXXXXXXXXX",
    "razorpay_payment_id": "pay_XXXXXXXXXXXXXX",
    "razorpay_signature": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Response (Success):**
Indicates that the payment was successful and the booking is confirmed.
```json
{
    "success": true,
    "message": "Payment verified successfully",
    "booking_id": 5
}
```

**Response (Failure):**
```json
{
    "success": false,
    "message": "Payment verification failed"
}
```
