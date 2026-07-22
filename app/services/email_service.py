import json
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from app.models.contact import AIAnalysis, ContactCreate


class EmailService:
    def __init__(
        self,
        *,
        mode: str,
        log_path: Path,
        owner_email: str,
        from_email: str,
        from_name: str,
        smtp_host: str | None,
        smtp_port: int,
        smtp_username: str | None,
        smtp_password: str | None,
        smtp_use_tls: bool,
    ) -> None:
        self.mode = mode
        self.log_path = log_path
        self.owner_email = owner_email
        self.from_email = from_email
        self.from_name = from_name
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls

    async def send_contact_emails(
        self, contact_id: str, contact: ContactCreate, analysis: AIAnalysis
    ) -> None:
        owner = self._owner_message(contact_id, contact, analysis)
        user = self._user_message(contact, analysis)
        if self.mode == "log":
            self._write_log(contact_id, owner, user)
            return
        if not self.smtp_host:
            raise RuntimeError("SMTP_HOST is required in smtp mode")
        await aiosmtplib.send(
            owner,
            hostname=self.smtp_host,
            port=self.smtp_port,
            username=self.smtp_username,
            password=self.smtp_password,
            start_tls=self.smtp_use_tls,
            timeout=10,
        )
        await aiosmtplib.send(
            user,
            hostname=self.smtp_host,
            port=self.smtp_port,
            username=self.smtp_username,
            password=self.smtp_password,
            start_tls=self.smtp_use_tls,
            timeout=10,
        )

    def _owner_message(
        self, contact_id: str, contact: ContactCreate, analysis: AIAnalysis
    ) -> EmailMessage:
        message = self._base_message(self.owner_email, f"New contact: {analysis.category.value}")
        message.set_content(
            f"Contact ID: {contact_id}\nName: {contact.name}\nPhone: {contact.phone}\n"
            f"Email: {contact.email}\nCategory: {analysis.category.value}\n"
            f"Sentiment: {analysis.sentiment.value}\nPriority: {analysis.priority}/5\n\n"
            f"Comment:\n{contact.comment}"
        )
        return message

    def _user_message(self, contact: ContactCreate, analysis: AIAnalysis) -> EmailMessage:
        message = self._base_message(str(contact.email), "We received your message")
        message.set_content(
            f"Hello, {contact.name}!\n\n{analysis.suggested_reply}\n\n"
            "Here is a copy of your message:\n"
            f"{contact.comment}\n\nThis is an automated confirmation."
        )
        return message

    def _base_message(self, recipient: str, subject: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = recipient
        message["Subject"] = subject
        return message

    def _write_log(self, contact_id: str, owner: EmailMessage, user: EmailMessage) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "contact_id": contact_id,
            "mode": "log",
            "recipients": [str(owner["To"]), str(user["To"])],
            "subjects": [str(owner["Subject"]), str(user["Subject"])],
        }
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
