import hashlib
import logging

from app.core.config import Settings
from app.core.exceptions import DeliveryError, RateLimitExceeded
from app.models.contact import ContactCreate, ContactResponse
from app.repositories.contact_repository import ContactRepository
from app.repositories.rate_limit_repository import RateLimitRepository
from app.services.ai_service import AIService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class ContactService:
    def __init__(
        self,
        settings: Settings,
        contacts: ContactRepository,
        rate_limits: RateLimitRepository,
        ai: AIService,
        email: EmailService,
    ) -> None:
        self.settings = settings
        self.contacts = contacts
        self.rate_limits = rate_limits
        self.ai = ai
        self.email = email

    async def submit(self, data: ContactCreate, client_identity: str) -> ContactResponse:
        identity_hash = hashlib.sha256(client_identity.encode()).hexdigest()
        retry_after = self.rate_limits.consume(
            identity_hash,
            self.settings.rate_limit_requests,
            self.settings.rate_limit_window_seconds,
        )
        if retry_after is not None:
            raise RateLimitExceeded(retry_after)

        analysis, fallback_used = await self.ai.analyze(data.comment, data.name)
        contact_id, created_at = self.contacts.create(data, analysis, fallback_used)
        try:
            await self.email.send_contact_emails(contact_id, data, analysis)
            self.contacts.set_delivery_status(contact_id, "delivered")
        except Exception:
            self.contacts.set_delivery_status(contact_id, "failed")
            logger.exception("Email delivery failed for contact_id=%s", contact_id)
            raise DeliveryError() from None

        return ContactResponse(
            id=contact_id,
            status="accepted",
            message="Your message has been received. A confirmation was sent to your email.",
            ai=analysis,
            ai_fallback_used=fallback_used,
            created_at=created_at,
        )
