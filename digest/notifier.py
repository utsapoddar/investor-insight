"""Send digest email via Gmail SMTP (no n8n dependency)."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from digest.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, LAST_DIGEST_PATH


def send(subject: str, html_body: str, recipients: list[str]) -> bool:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[notifier] GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping email.")
        _save_fallback(html_body)
        return False

    if not recipients:
        print("[notifier] No recipients configured — skipping email.")
        _save_fallback(html_body)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Alpha Digest <{GMAIL_ADDRESS}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())
        print(f"[notifier] Digest sent to {len(recipients)} recipient(s).")
        return True
    except Exception as e:
        print(f"[notifier] Email failed: {e}")
        _save_fallback(html_body)
        return False


def _save_fallback(html_body: str):
    LAST_DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_DIGEST_PATH.write_text(html_body, encoding="utf-8")
    print(f"[notifier] Digest saved to {LAST_DIGEST_PATH}")
