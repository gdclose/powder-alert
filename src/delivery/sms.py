"""SMS delivery via Twilio."""

from twilio.rest import Client
from ..config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER


def send_sms(to_number: str, message: str) -> bool:
    """Send an SMS message via Twilio.

    Args:
        to_number: Recipient phone number (E.164 format, e.g. +14155551234)
        message: Message body (Twilio max 1600 chars per segment)

    Returns:
        True if sent successfully, False otherwise
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("Twilio credentials not configured. Set TWILIO_* env vars.")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number,
        )
        print(f"SMS sent: {msg.sid}")
        return True
    except Exception as e:
        print(f"SMS failed: {e}")
        return False
