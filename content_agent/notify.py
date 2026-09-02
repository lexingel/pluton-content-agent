"""
Sends a notification email with the draft, before it auto-publishes.

Requires env vars:
  GMAIL_ADDRESS       -- the Gmail address sending the notification
  GMAIL_APP_PASSWORD  -- a Gmail "App Password" (NOT your normal password;
                          generate one at myaccount.google.com/apppasswords)
  NOTIFY_TO_ADDRESS   -- where the notification should be sent (can be the
                          same address, or plutonpdrm@gmail.com)
"""
import os
import smtplib
from email.mime.text import MIMEText

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
NOTIFY_TO_ADDRESS = os.environ.get("NOTIFY_TO_ADDRESS", GMAIL_ADDRESS)
DELAY_HOURS = float(os.environ.get("PUBLISH_DELAY_HOURS", "3"))


def send_review_email(post: dict, cancel_instructions: str):
    subject = f"[Plüton İçerik Botu] Yeni taslak: {post['title']}"
    body = f"""Bugünkü otomatik içerik üretildi ve {DELAY_HOURS} saat içinde otomatik yayınlanacak.

BAŞLIK: {post['title']}

BLOG YAZISI:
{post['blog_html_body']}

INSTAGRAM CAPTION:
{post['ig_caption']}

---
İptal etmek isterseniz: {cancel_instructions}
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = NOTIFY_TO_ADDRESS

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)


if __name__ == "__main__":
    demo_post = {
        "title": "Test",
        "blog_html_body": "<p>test</p>",
        "ig_caption": "test caption",
    }
    send_review_email(demo_post, "Repo'daki CANCEL_TODAY dosyasını ekleyin.")
    print("Sent.")
