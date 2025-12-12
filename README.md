# Dandeli-Vintage-Resorts
# Django Resort Booking API

This project is a Django-based REST API for a resort booking system. It features a robust, multi-step booking process designed to prevent booking conflicts and provide a seamless user experience, with payment handling powered by Razorpay.

## Features

- **Phone Number Authentication:** Secure and simple user login/signup using OTP.
- **Profile Management:** Users can update their personal information.
- **Robust Booking Flow:** A multi-step process that includes:
    1.  Searching for available rooms by location.
    2.  Creating a temporary "booking attempt" after selecting rooms.
    3.  Adding guest details.
    4.  Initiating payment with Razorpay.
    5.  Confirming the booking upon successful payment verification via a secure webhook.
- **Scalable Architecture:** The separation of booking attempts from final bookings minimizes race conditions and improves reliability.

## Getting Started

### Prerequisites

-   Nix package manager
-   Firebase CLI (for deployment)

### Setup & Running the Server

1.  **Activate the environment:** The project uses a Nix shell. Most IDEs with Nix integration (like the one you are using) will automatically activate it. To do it manually, run `nix-shell` in the project root.

2.  **Set Environment Variables:** This project requires several environment variables for security and payment integration. You should set them in your shell environment.

    ```bash
    export DJANGO_SECRET_KEY='your-django-secret-key'
    export RAZORPAY_KEY_ID='your-razorpay-key-id'
    export RAZORPAY_KEY_SECRET='your-razorpay-key-secret'
    export RAZORPAY_WEBHOOK_SECRET='your-razorpay-webhook-secret'
    ```
    See the "Environment Variables" section for more details.

3.  **Activate Python virtual environment:**
    ```bash
    source .venv/bin/activate
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r mysite/requirements.txt
    ```

5.  **Apply database migrations:**
    ```bash
    python mysite/manage.py migrate
    ```

6.  **Start the development server:**
    ```bash
    ./devserver.sh
    ```
    The API will be available at `http://localhost:8000`.

## Environment Variables

-   `DJANGO_SECRET_KEY`: A secret key for a particular Django installation. This is used to provide cryptographic signing, and should be set to a unique, unpredictable value.
-   `RAZORPAY_KEY_ID`: Your Razorpay Key ID.
-   `RAZORPAY_KEY_SECRET`: Your Razorpay Key Secret.
-   `RAZORPAY_WEBHOOK_SECRET`: The secret you configure in your Razorpay webhook settings. This is used to verify that incoming webhook requests are genuinely from Razorpay.

## API Documentation

All endpoints require authentication unless otherwise specified. Authentication is handled via JWT tokens provided during the OTP verification process.

### Authentication

---

#### `POST /api/auth/otp/request/`

Initiates the login or registration process by sending an OTP to the user's phone number.

**Request Body:**
```json
{
    "phone_number": "9999988888"
}
```

---

#### `POST /api/auth/otp/verify/`

Verifies the OTP and, if valid, returns JWT access and refresh tokens. A new user is created if one doesn't already exist.

**Request Body:**
```json
{
    "phone_number": "9999988888",
    "otp": "123456"
}
```

---

### Profile Management

---

#### `POST /api/auth/profile/update/`

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

---

### Booking Flow

The booking process is a sequence of API calls.

---

#### 1. `GET /api/rooms/search/`

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

---

#### 2. `POST /api/booking/select-rooms/`

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

---

#### 3. `POST /api/booking/add-guests/`

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

---

#### 4. `POST /api/booking/initiate-payment/`

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
    "amount": 75000.00
}
```
The frontend should use the `razorpay_order_id` and `razorpay_key` to open the Razorpay payment dialog.

---

#### 5. `POST /api/booking/payment-callback/`

A **webhook endpoint** for Razorpay to send payment status updates. This endpoint is **not for direct client use**. It must be configured in the Razorpay dashboard for the `payment.captured` event.

**Behavior:**
-   The endpoint uses the `RAZORPAY_WEBHOOK_SECRET` to verify the signature of the incoming request, ensuring it's from Razorpay.
-   If the payment is successful (`payment.captured` event), the system converts the `BookingAttempt` into a `FinalBooking`, permanently reserving the rooms.
-   If the payment fails or the signature is invalid, the booking attempt is marked as failed and the rooms are released.
