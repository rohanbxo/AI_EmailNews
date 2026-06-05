"""Send HTML email via Gmail SMTP."""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage


log = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, html: str, text: str = "") -> None:
    sender = os.getenv("MY_EMAIL")
    password = os.getenv("APP_PASSWORD")
    if not sender or not password:
        raise RuntimeError("MY_EMAIL and APP_PASSWORD must be set in the environment")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text or "Your email client does not support HTML.")
    msg.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password)
        server.send_message(msg)
    log.info("Email sent to %s (subject=%r)", to, subject)
