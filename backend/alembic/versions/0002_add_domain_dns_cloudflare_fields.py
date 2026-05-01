"""add cloudflare dns metadata fields to domains

Revision ID: 0002_add_domain_dns_cloudflare_fields
Revises: 0001_initial
Create Date: 2026-04-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_domain_dns_cf"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("domains", sa.Column("cloudflare_zone_id", sa.String(length=64), nullable=True))
    op.add_column(
        "domains",
        sa.Column("cloudflare_auto_dns", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "domains",
        sa.Column("dns_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("domains", sa.Column("dns_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("domains", "dns_verified_at")
    op.drop_column("domains", "dns_verified")
    op.drop_column("domains", "cloudflare_auto_dns")
    op.drop_column("domains", "cloudflare_zone_id")
