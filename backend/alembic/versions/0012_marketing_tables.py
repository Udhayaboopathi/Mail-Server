"""add marketing and transactional tables

Revision ID: 0012_marketing_tables
Revises: 0011_team_enterprise_tables
Create Date: 2026-05-01 00:00:04.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_marketing_tables"
down_revision = "0011_team_enterprise_tables"
branch_labels = None
depends_on = None


uuid_pk = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "email_tracking_pixels",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("read_receipt_id", uuid_pk, sa.ForeignKey("read_receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("token", name="uq_email_tracking_pixels_token"),
    )

    op.create_table(
        "email_link_clicks",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("read_receipt_id", uuid_pk, sa.ForeignKey("read_receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("tracking_token", sa.String(length=64), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("first_clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tracking_token", name="uq_email_link_clicks_tracking_token"),
    )

    op.create_table(
        "unsubscribe_tokens",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sender_mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_email", sa.String(length=319), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("token", name="uq_unsubscribe_tokens_token"),
        sa.UniqueConstraint("sender_mailbox_id", "recipient_email", name="uq_unsubscribe_tokens_sender_recipient"),
    )

    op.create_table(
        "unsubscribe_list",
        sa.Column("sender_mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_email", sa.String(length=319), nullable=False),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("sender_mailbox_id", "recipient_email", name="pk_unsubscribe_list"),
    )

    op.create_table(
        "webhooks",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{receive,send,bounce}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "campaign_emails",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("from_name", sa.String(length=100), nullable=True),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unsubscribe_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("campaign_emails")
    op.drop_table("webhooks")
    op.drop_table("unsubscribe_list")
    op.drop_table("unsubscribe_tokens")
    op.drop_table("email_link_clicks")
    op.drop_table("email_tracking_pixels")
