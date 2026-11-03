"""Add extractions, extraction_cells, rob_assessments tables + extraction_schema column

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES_WITH_RLS = ["extractions", "extraction_cells", "rob_assessments"]


def upgrade() -> None:
    op.add_column("protocols", sa.Column("extraction_schema", sa.JSON(), nullable=True))

    op.create_table(
        "extractions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("schema_version", sa.String(100), nullable=False, server_default="cochrane-default-v1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("degradado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alertas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "document_id", name="uq_extraction_review_document"),
    )

    op.create_table(
        "extraction_cells",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("extraction_id", sa.UUID(), sa.ForeignKey("extractions.id"), nullable=False),
        sa.Column("field", sa.String(255), nullable=False),
        sa.Column("block", sa.String(100), nullable=False, server_default=""),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("value_type", sa.String(50), nullable=False, server_default="text"),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(50), nullable=False, server_default="low"),
        sa.Column("needs_human_confirmation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("flags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "rob_assessments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("instrument", sa.String(50), nullable=False, server_default="rob2"),
        sa.Column("overall_judgment", sa.String(50), nullable=False),
        sa.Column("domain_results", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("degradado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alertas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "document_id", "instrument", name="uq_rob_review_document_instrument"),
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
    op.drop_column("protocols", "extraction_schema")
