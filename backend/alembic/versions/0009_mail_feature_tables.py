"""add mail feature tables

Revision ID: 0009_mail_feature_tables
Revises: 0008_security_tables
Create Date: 2026-05-01 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_mail_feature_tables"
down_revision = "0008_security_tables"
branch_labels = None
depends_on = None


uuid_pk = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "email_threads",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("participants", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("has_unread", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        "ALTER TABLE mailboxes "
        "ADD COLUMN IF NOT EXISTS thread_id UUID REFERENCES email_threads(id) ON DELETE SET NULL"
    )

    op.create_table(
        "labels",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False, server_default=sa.text("'#6366f1'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("mailbox_id", "name", name="uq_labels_mailbox_name"),
    )

    op.create_table(
        "email_labels",
        sa.Column("email_uid", sa.String(length=50), nullable=False),
        sa.Column("label_id", uuid_pk, sa.ForeignKey("labels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("email_uid", "label_id", name="pk_email_labels"),
    )

    op.create_table(
        "email_rules",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("match_type", sa.String(length=10), nullable=False, server_default=sa.text("'any'")),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "email_templates",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "read_receipts",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sender_mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=False),
        sa.Column("recipient_email", sa.String(length=319), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "pgp_keys",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("private_key_encrypted", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=40), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("mailbox_id", name="uq_pgp_keys_mailbox_id"),
        sa.UniqueConstraint("fingerprint", name="uq_pgp_keys_fingerprint"),
    )


def downgrade() -> None:
    op.drop_table("pgp_keys")
    op.drop_table("read_receipts")
    op.drop_table("email_templates")
    op.drop_table("email_rules")
    op.drop_table("email_labels")
    op.drop_table("labels")
    op.execute("ALTER TABLE mailboxes DROP COLUMN IF EXISTS thread_id")
    op.drop_table("email_threads")
