import os
import smtplib
from email.message import EmailMessage


SMTP_EMAIL = os.environ["SMTP_EMAIL"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
RECEIVER_EMAIL = os.environ["RECEIVER_EMAIL"]


def send_contact_email(name: str, email: str, message: str):
    msg = EmailMessage()

    msg["Subject"] = f"New Portfolio Contact from {name}"
    msg["From"] = SMTP_EMAIL
    msg["To"] = RECEIVER_EMAIL

    msg.set_content(
        f"""
You have received a new message from your portfolio website.

Name:
{name}

Email:
{email}

Message:
{message}
"""
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
        smtp.send_message(msg)