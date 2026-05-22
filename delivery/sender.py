"""
Email Sender
Sends the formatted HTML email via Gmail SMTP.
Embeds the header image as a CID attachment for universal email client support.
"""

import smtplib
import os
import yaml
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
from datetime import datetime
from pathlib import Path


HEADER_IMAGE = Path(__file__).parent / "assets" / "header.jpg"


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def send_email(html_content: str, config: dict = None) -> bool:
    """
    Send the newsletter email via SMTP.

    Requires environment variable: NEWSLETTER_SMTP_PASSWORD
    (This is an app password generated in Google account settings)

    Returns True if sent successfully, False otherwise.
    """
    if config is None:
        config = load_config()

    delivery = config["delivery"]
    # Support single address or list of addresses
    to_config = delivery["to"]
    if isinstance(to_config, list):
        to_addrs = to_config
    else:
        to_addrs = [to_config]
    from_addr = delivery["from"]
    sender_name = delivery.get("sender_name", "The Daily Briefing")
    smtp_server = delivery["smtp_server"]
    smtp_port = delivery["smtp_port"]

    # Get password from environment
    password = os.environ.get("NEWSLETTER_SMTP_PASSWORD")
    if not password:
        print("[ERROR] NEWSLETTER_SMTP_PASSWORD environment variable not set.")
        print("  Generate an app password at: https://myaccount.google.com/apppasswords")
        return False

    # Build the email with related parts (for CID image embedding)
    today = datetime.now().strftime("%B %d, %Y")
    subject = f"{delivery['subject_prefix']}  |  {today}"

    # Outer: "related" wraps the content + inline images
    msg_root = MIMEMultipart("related")
    msg_root["Subject"] = subject
    msg_root["From"] = formataddr((sender_name, from_addr))
    msg_root["To"] = ", ".join(to_addrs)

    # Inner: "alternative" holds plain text + HTML
    msg_alt = MIMEMultipart("alternative")
    msg_root.attach(msg_alt)

    # Plain text fallback
    plain_text = "Your Daily Briefing is ready. View this email in HTML for the full experience."
    msg_alt.attach(MIMEText(plain_text, "plain"))

    # HTML content
    msg_alt.attach(MIMEText(html_content, "html"))

    # Embed header image as inline attachment
    if HEADER_IMAGE.exists():
        with open(HEADER_IMAGE, "rb") as img_f:
            img = MIMEImage(img_f.read(), _subtype="jpeg")
            img.add_header("Content-ID", "<header-image>")
            img.add_header("Content-Disposition", "inline", filename="header.jpg")
            msg_root.attach(img)
    else:
        print(f"[WARN] Header image not found at {HEADER_IMAGE}")

    # Send
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, to_addrs, msg_root.as_string())

        print(f"[OK] Newsletter sent to {', '.join(to_addrs)}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[ERROR] SMTP authentication failed.")
        print("  Check that your app password is correct.")
        print("  Generate at: https://myaccount.google.com/apppasswords")
        return False
    except smtplib.SMTPException as e:
        print(f"[ERROR] SMTP error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error sending email: {e}")
        return False


if __name__ == "__main__":
    test_html = """
    <html><body>
    <h1>Test Newsletter</h1>
    <p>If you see this, email delivery is working correctly.</p>
    <p>Sent at: {}</p>
    </body></html>
    """.format(datetime.now().isoformat())

    success = send_email(test_html)
    if success:
        print("Test email sent successfully!")
    else:
        print("Failed to send test email. Check configuration.")
