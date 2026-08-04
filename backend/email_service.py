import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def is_configured() -> bool:
    """Return True if all required SMTP environment variables are set."""
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SENDER_EMAIL", "").strip()
    return bool(host and user and password and sender)

def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via SMTP. If not configured, logs it and returns True."""
    if not is_configured():
        print(f"\n[EMAIL_SERVICE] NOT CONFIGURED. Mocking email send to {to_email}")
        print(f"[EMAIL_SERVICE] Subject: {subject}")
        print(f"[EMAIL_SERVICE] Body length: {len(html_body)} chars\n")
        return True
    
    host = os.getenv("SMTP_HOST", "").strip()
    port_str = os.getenv("SMTP_PORT", "587").strip()
    port = int(port_str) if port_str.isdigit() else 587
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SENDER_EMAIL", "").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email

    part_html = MIMEText(html_body, "html")
    msg.attach(part_html)

    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(user, password)
        server.sendmail(sender, to_email, msg.as_string())
        server.quit()
        print(f"[EMAIL_SERVICE] Successfully sent email to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL_SERVICE] Failed to send email to {to_email}: {e}")
        return False
