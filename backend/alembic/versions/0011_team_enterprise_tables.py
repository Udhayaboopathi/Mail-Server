"""add team and enterprise tables

Revision ID: 0011_team_enterprise_tables
Revises: 0010_productivity_tables
Create Date: 2026-05-01 00:00:03.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_team_enterprise_tables"
down_revision = "0010_productivity_tables"
branch_labels = None
depends_on = None


uuid_pk = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "shared_mailboxes",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain_id", uuid_pk, sa.ForeignKey("domains.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("mailbox_id", name="uq_shared_mailboxes_mailbox_id"),
    )

    op.create_table(
        "shared_mailbox_members",
        sa.Column("shared_mailbox_id", uuid_pk, sa.ForeignKey("shared_mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", uuid_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False, server_default=sa.text("'read_write'")),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("shared_mailbox_id", "user_id", name="pk_shared_mailbox_members"),
    )

    op.create_table(
        "mailbox_delegations",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delegate_user_id", uuid_pk, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False, server_default=sa.text("'send_on_behalf'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("owner_mailbox_id", "delegate_user_id", name="uq_mailbox_delegations_owner_delegate"),
    )


def downgrade() -> None:
    op.drop_table("mailbox_delegations")
    op.drop_table("shared_mailbox_members")
    op.drop_table("shared_mailboxes")
