from __future__ import annotations


class VoiceAgentError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        category: str,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category
        self.status_code = status_code


class AuthenticationError(VoiceAgentError):
    def __init__(self, message: str = "API key is missing or invalid") -> None:
        super().__init__(
            code="authentication_error",
            message=message,
            category="auth",
            status_code=401,
        )


class AuthorizationError(VoiceAgentError):
    def __init__(self, message: str = "API key does not have the required scope") -> None:
        super().__init__(
            code="authorization_error",
            message=message,
            category="auth",
            status_code=403,
        )


class NotFoundError(VoiceAgentError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(
            code="not_found",
            message=message,
            category="validation",
            status_code=404,
        )


class InvalidSignatureError(VoiceAgentError):
    def __init__(self, message: str = "Webhook signature is invalid") -> None:
        super().__init__(
            code="invalid_signature",
            message=message,
            category="auth",
            status_code=401,
        )


class UpstreamServiceError(VoiceAgentError):
    def __init__(self, message: str = "Upstream service error", status_code: int = 502) -> None:
        super().__init__(
            code="upstream_service_error",
            message=message,
            category="integration",
            status_code=status_code,
        )


class IdempotencyConflictError(VoiceAgentError):
    def __init__(self, message: str = "Idempotency key already used with different payload") -> None:
        super().__init__(
            code="idempotency_conflict",
            message=message,
            category="validation",
            status_code=409,
        )


class IdempotencyRequiredError(VoiceAgentError):
    def __init__(self, message: str = "Idempotency-Key header is required") -> None:
        super().__init__(
            code="idempotency_required",
            message=message,
            category="validation",
            status_code=428,
        )


class BookingConflictError(VoiceAgentError):
    def __init__(self, message: str = "Requested booking slot is no longer available") -> None:
        super().__init__(
            code="booking_conflict",
            message=message,
            category="validation",
            status_code=409,
        )
