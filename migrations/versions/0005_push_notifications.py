"""push notifications

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "push_subscription",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    op.create_table(
        "match_notification",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("match.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("n_recipients", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('pre', 'post')", name="match_notification_kind_check"),
        sa.UniqueConstraint("match_id", "kind", name="match_notification_unique"),
    )


def downgrade() -> None:
    op.drop_table("match_notification")
    op.drop_table("push_subscription")
