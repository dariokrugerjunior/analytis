"""VAPID config — private/public keypair + subject for Web Push signing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VapidConfig:
    private_key: str
    public_key: str
    subject: str


def load_vapid_config(
    *,
    private_key: str | None,
    public_key: str | None,
    subject: str,
) -> VapidConfig:
    """Build VapidConfig from settings values; raise if essentials missing."""
    if not private_key:
        raise ValueError("VAPID private key missing (set ANALYTIS_VAPID_PRIVATE_KEY)")
    if not public_key:
        raise ValueError("VAPID public key missing (set ANALYTIS_VAPID_PUBLIC_KEY)")
    return VapidConfig(private_key=private_key, public_key=public_key, subject=subject)
