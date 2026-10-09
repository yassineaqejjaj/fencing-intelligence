import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage

import structlog

from fencing_api.config import get_settings

log = structlog.get_logger()


@dataclass
class Outbox:
    messages: list[dict] = field(default_factory=list)


OUTBOX = Outbox()


def send_email(to: str, subject: str, body: str) -> bool:
    """Queue or send one transactional email. Returns True when the message
    was handed to SMTP (or to the dev outbox), False when email is not
    configured and the message was dropped. Callers must surface False to
    operators instead of pretending the email was sent."""
    settings = get_settings()
    message = {"to": to, "subject": subject, "body": body}
    if settings.environment != "production":
        OUTBOX.messages.append(message)
    if not settings.smtp_host:
        log.warning("email_dropped_no_smtp", subject=subject)
        return False
    email = EmailMessage()
    email["From"] = settings.smtp_from
    email["To"] = to
    email["Subject"] = subject
    email.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        if settings.smtp_starttls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(email)
    return True
