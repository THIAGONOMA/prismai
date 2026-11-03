"""Add documents, eligibility_decisions, evidence_spans tables with RLS

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES_WITH_RLS = ["documents", "eligibility_decisions", "evidence_spans"]


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("record_id", sa.UUID(), sa.ForeignKey("records.id"), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("n_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("extraction_method", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("fetch_source", sa.String(50), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "record_id", name="uq_document_review_record"),
    )

    op.create_table(
        "eligibility_decisions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(50), nullable=False, server_default=""),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("degradado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alertas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "document_id", name="uq_eligibility_review_document"),
    )

    op.create_table(
        "evidence_spans",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("criterion", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
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
