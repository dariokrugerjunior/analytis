"""FastAPI dependency providers."""

from fastapi import Depends, Header, HTTPException, status

from analytis.config import Settings, get_settings


def require_api_key(
    settings: Settings = Depends(get_settings),  # noqa: B008
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not x_api_key or x_api_key != settings.api_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
