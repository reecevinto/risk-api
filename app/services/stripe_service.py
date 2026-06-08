import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_checkout_session(price_id: str, customer_email: str):

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],

        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],

        mode="subscription",

        customer_email=customer_email,

        success_url="http://localhost:8000/success",
        cancel_url="http://localhost:8000/cancel",
    )

    return session