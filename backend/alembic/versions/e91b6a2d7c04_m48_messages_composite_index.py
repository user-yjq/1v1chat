"""M4.8 messages (conversation_id, sent_at) 联合索引

Revision ID: e91b6a2d7c04
Revises: c4a2e8f0b1d5
Create Date: 2026-09-06 13:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e91b6a2d7c04"
down_revision: str | None = "c4a2e8f0b1d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_messages_conversation_sent_at",
        "messages",
        ["conversation_id", "sent_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_sent_at", table_name="messages")
