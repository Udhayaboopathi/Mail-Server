"""add admin and compliance tables

Revision ID: 0013_admin_compliance_tables
Revises: 0012_marketing_tables
Create Date: 2026-05-01 00:00:05.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_admin_compliance_tables"
down_revision = "0012_marketing_tables"
branch_labels = None
depends_on = None


uuid_pk = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute("ALTER TABLE domains ADD COLUMN IF NOT EXISTS whitelabel_logo_url TEXT")
    op.execute(
        "ALTER TABLE domains "
        "ADD COLUMN IF NOT EXISTS whitelabel_primary_color VARCHAR(7) DEFAULT '#6366f1'"
    )
    op.execute("ALTER TABLE domains ADD COLUMN IF NOT EXISTS whitelabel_company_name VARCHAR(100)")
    op.execute("ALTER TABLE domains ADD COLUMN IF NOT EXISTS retention_days INTEGER DEFAULT 0")
    op.execute("ALTER TABLE domains ADD COLUMN IF NOT EXISTS ediscovery_enabled BOOLEAN DEFAULT false")

    op.create_table(
        "ediscovery_exports",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("domain_id", uuid_pk, sa.ForeignKey("domains.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", uuid_pk, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("query", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("total_messages", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "spam_reports",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email_uid", sa.String(length=50), nullable=False),
        sa.Column("from_address", sa.String(length=319), nullable=False),
        sa.Column("report_type", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("spam_reports")
    op.drop_table("ediscovery_exports")
    op.execute("ALTER TABLE domains DROP COLUMN IF EXISTS ediscovery_enabled")
    op.execute("ALTER TABLE domains DROP COLUMN IF EXISTS retention_days")
    op.execute("ALTER TABLE domains DROP COLUMN IF EXISTS whitelabel_company_name")
    op.execute("ALTER TABLE domains DROP COLUMN IF EXISTS whitelabel_primary_color")
    op.execute("ALTER TABLE domains DROP COLUMN IF EXISTS whitelabel_logo_url")
