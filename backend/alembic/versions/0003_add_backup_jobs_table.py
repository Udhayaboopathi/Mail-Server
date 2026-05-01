"""add backup jobs table

Revision ID: 0003_add_backup_jobs_table
Revises: 0002_add_domain_dns_cloudflare_fields
Create Date: 2026-04-30 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_add_backup_jobs_table"
down_revision = "0002_domain_dns_cf"
branch_labels = None
depends_on = None


uuid_pk = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "backup_jobs",
        sa.Column("id", uuid_pk, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mailbox_id", uuid_pk, sa.ForeignKey("mailboxes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_size_mb", sa.Float(), nullable=True),
        sa.Column("total_messages", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("backup_jobs")
