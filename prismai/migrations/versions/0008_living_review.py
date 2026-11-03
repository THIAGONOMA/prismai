"""Add living_updates table and living columns to reviews (M8)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-21
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES_WITH_RLS = ["living_updates"]


def upgrade() -> None:
    op.create_table(
        "living_updates",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("trigger", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("search_sources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("new_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("screening_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("impact_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("impact_result", sa.JSON(), nullable=True),
        sa.Column("notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("reviews", sa.Column("living_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("reviews", sa.Column("living_cron", sa.String(100), nullable=True))
    op.add_column("reviews", sa.Column("living_last_run_at", sa.DateTime(timezone=True), nullable=True))

    for table in _TABLES_WITH_RLS:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            "USING (org_id::text = current_setting('app.current_org', true)) "
            "WITH CHECK (org_id::text = current_setting('app.current_org', true))"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO prismai_app")


def downgrade() -> None:
    for table in reversed(_TABLES_WITH_RLS):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.drop_table(table)

    op.drop_column("reviews", "living_last_run_at")
    op.drop_column("reviews", "living_cron")
    op.drop_column("reviews", "living_enabled")
