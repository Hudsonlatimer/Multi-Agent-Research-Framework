"""Errors the CLI can name without dumping a stack trace."""


class ResearchError(Exception):
    """A research run failed in a way the caller can act on."""

    def __init__(self, provider: str, kind: str, message: str) -> None:
        self.provider = provider
        self.kind = kind
        super().__init__(message)


def classify_provider_error(provider: str, exc: Exception) -> ResearchError:
    """Turn a provider exception into a missing-key, rate-limit, or request error."""
    if isinstance(exc, ResearchError):
        return exc
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    text = f"{exc}".lower()
    if (
        status == 429
        or "rate limit" in text
        or "too many requests" in text
        or "tokens per day" in text
    ):
        return ResearchError(
            provider,
            "rate_limit",
            f"{provider} rate limit reached. Wait and retry, or switch LLM_PROVIDER.",
        )
    if (
        status in {401, 403}
        or "api key" in text
        or "unauthorized" in text
        or "permission denied" in text
    ):
        return ResearchError(
            provider,
            "missing_key",
            f"{provider} rejected the credentials. Check the API key in the environment.",
        )
    return ResearchError(provider, "provider_error", f"{provider} request failed: {exc}")
