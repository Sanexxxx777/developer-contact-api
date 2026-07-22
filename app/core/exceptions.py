class AppError(Exception):
    def __init__(self, message: str, status_code: int, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class RateLimitExceeded(AppError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many requests. Please try again later.", 429, "rate_limit_exceeded")
        self.retry_after = retry_after


class DeliveryError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Your request was saved, but email delivery failed. Please try again later.",
            503,
            "email_delivery_failed",
        )
