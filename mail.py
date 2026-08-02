import os
import requests

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
RECEIVER_EMAIL = os.environ["RECEIVER_EMAIL"]


def send_contact_email(name: str, email: str, message: str):
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Portfolio Contact <onboarding@resend.dev>",
            "to": [RECEIVER_EMAIL],
            "subject": f"New Portfolio Contact from {name}",
            "reply_to": email,
            "text": f"""
Name:
{name}

Email:
{email}

Message:
{message}
""",
        },
        timeout=15,
    )

    response.raise_for_status()