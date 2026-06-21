"""CLI: analytis push (dispatch + generate-vapid-keys)."""

from __future__ import annotations

import asyncio
import base64

import typer
from py_vapid import Vapid  # type: ignore[import-untyped]

from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.push.dispatcher import PushDispatcher
from analytis.push.vapid import load_vapid_config

app = typer.Typer(help="Web Push notifications.")


@app.command("dispatch")
def dispatch() -> None:
    """Run one dispatch cycle: detect pre/post matches and send pushes."""
    settings = get_settings()
    private_key = (
        settings.vapid_private_key.get_secret_value()
        if settings.vapid_private_key is not None
        else None
    )
    vapid = load_vapid_config(
        private_key=private_key,
        public_key=settings.vapid_public_key,
        subject=settings.vapid_subject,
    )
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    dispatcher = PushDispatcher(factory, vapid)
    result = asyncio.run(dispatcher.dispatch())
    typer.echo(
        f"pre={result.pre_matches} post={result.post_matches} "
        f"subs={result.subscribers} sent={result.successes} deleted={result.deleted}"
    )


@app.command("generate-vapid-keys")
def generate_vapid_keys() -> None:
    """Generate a fresh VAPID keypair and print as base64 url-safe strings."""
    vapid = Vapid()
    vapid.generate_keys()
    priv_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    pub = vapid.public_key
    # Uncompressed EC point format: 0x04 || X (32 bytes) || Y (32 bytes)
    pub_numbers = pub.public_numbers()
    pub_bytes = b"\x04" + pub_numbers.x.to_bytes(32, "big") + pub_numbers.y.to_bytes(32, "big")
    priv_b64 = base64.urlsafe_b64encode(priv_raw).rstrip(b"=").decode()
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    typer.echo(f"ANALYTIS_VAPID_PRIVATE_KEY={priv_b64}")
    typer.echo(f"ANALYTIS_VAPID_PUBLIC_KEY={pub_b64}")
    typer.echo("# Copy these to deploy/.env.prod (do NOT commit)")
