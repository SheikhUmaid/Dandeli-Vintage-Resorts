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
    4.  Creating a Razorpay order.
    5.  Confirming the booking upon successful client-side payment verification.
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

---

#### 3. `POST /api/booking/add-guests/`

Adds the details for each guest to the booking attempt.

**Request Body:**
```json
{
    "booking_attempt_id": 123,
    "guests": [
        {"room_id": 101, "name": "Alice", "age": 30}
    ]
}
```

---

#### 4. `POST /api/booking/create-order/`

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
    "order_id": "order_XXXXXXXXXXXXXX",
    "amount": 3750000,
    "currency": "INR",
    "key": "rzp_test_XXXXXXXXXXXXXX",
    "booking_attempt_id": 123,
    "payment_id": 45
}
```

---

#### 5. `POST /api/booking/verify-payment/`

After the user completes the payment, the frontend calls this endpoint to verify the payment signature. If successful, the booking is confirmed.

**Request Body:**
```json
{
    "razorpay_order_id": "order_XXXXXXXXXXXXXX",
    "razorpay_payment_id": "pay_XXXXXXXXXXXXXX",
    "razorpay_signature": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Response (Success):**
```json
{
    "success": true,
    "message": "Payment verified successfully",
    "booking_id": 5
}
```
