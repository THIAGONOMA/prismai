"""Add import_runs and reports tables for PRISMA report (M7)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-21
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES_WITH_RLS = ["import_runs", "reports"]


def upgrade() -> None:
    op.create_table(
        "import_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("total_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False, server_default="prisma"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("flow_counts", sa.JSON(), nullable=True),
        sa.Column("discrepancies", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("checklist", sa.JSON(), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("artifacts", sa.JSON(), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("degradado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alertas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "kind", name="uq_report_review_kind"),
    )

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
