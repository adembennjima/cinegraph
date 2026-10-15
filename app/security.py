"""API-key authentication for the AI endpoint."""

from secrets import compare_digest
from typing import Annotated

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import Settings


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    api_key: Annotated[str | None, Security(API_KEY_HEADER)],
) -> None:
    """Reject requests without the configured application key."""
    expected = Settings().app_api_key.get_secret_value()

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Application authentication is not configured.",
        )

    if api_key is None or not compare_digest(
        api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key.",
        )
