"""add autoresponder tables

Revision ID: 0004_add_autoresponder_tables
Revises: 0003_add_backup_jobs_table
Create Date: 2026-04-30 00:31:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_add_autoresponder_tables"
down_revision = "0003_add_backup_jobs_table"
branch_labels = None
depends_on = None


uuid_pk = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "autoresponders",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("subject", sa.String(length=255), nullable=False, server_default=sa.text("'Out of Office'")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("reply_once_per_sender", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "autoresponder_sent",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("autoresponder_id", uuid_pk, sa.ForeignKey("autoresponders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sent_to", sa.String(length=319), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("autoresponder_sent")
    op.drop_table("autoresponders")
