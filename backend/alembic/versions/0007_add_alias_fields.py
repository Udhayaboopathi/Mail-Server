"""add alias catch-all and forward-only fields

Revision ID: 0007_add_alias_fields
Revises: 0006_add_contacts_table
Create Date: 2026-04-30 00:34:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_add_alias_fields"
down_revision = "0006_add_contacts_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("aliases", sa.Column("is_catch_all", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("aliases", sa.Column("forward_only", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    op.drop_column("aliases", "forward_only")
    op.drop_column("aliases", "is_catch_all")
