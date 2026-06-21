import pytest

from analytis.push.vapid import VapidConfig, load_vapid_config


def test_load_vapid_config_from_settings() -> None:
    cfg = load_vapid_config(
        private_key="priv",
        public_key="pub",
        subject="mailto:test@example.com",
    )
    assert isinstance(cfg, VapidConfig)
    assert cfg.private_key == "priv"
    assert cfg.public_key == "pub"
    assert cfg.subject == "mailto:test@example.com"


def test_load_vapid_config_missing_private_raises() -> None:
    with pytest.raises(ValueError, match="VAPID private key"):
        load_vapid_config(private_key=None, public_key="pub", subject="mailto:x@y.z")


def test_load_vapid_config_missing_public_raises() -> None:
    with pytest.raises(ValueError, match="VAPID public key"):
        load_vapid_config(private_key="priv", public_key=None, subject="mailto:x@y.z")
