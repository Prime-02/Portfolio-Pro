# gmail_utils.py
import requests
import base64
from email.mime.text import MIMEText
from app.config import settings


CLIENT_ID = settings.GOOGLE_CLIENT_ID
CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
REFRESH_TOKEN = settings.GMAIL_REFRESH_TOKEN


def get_access_token():
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }

    response = requests.post(token_url, data=payload)
    if response.ok:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to refresh token: {response.text}")


def send_email(to: str, subject: str, body: str):
    access_token = get_access_token()

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    data = {"raw": raw_message}

    response = requests.post(url, headers=headers, json=data)
    if response.ok:
        print("✅ Email sent successfully.")
    else:
        print("❌ Failed to send email:", response.text)
