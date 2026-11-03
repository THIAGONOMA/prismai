"""Add screener to decisions, create conflicts table with RLS

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("screener", sa.String(50), nullable=False, server_default="primary"))

    op.drop_constraint("uq_decision_review_registro", "decisions", type_="unique")
    op.create_unique_constraint(
        "uq_decision_review_registro_screener", "decisions", ["review_id", "registro_id", "screener"],
    )

    op.create_table(
        "conflicts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("registro_id", sa.String(255), nullable=False),
        sa.Column("decision_a", sa.String(50), nullable=False),
        sa.Column("decision_b", sa.String(50), nullable=False),
        sa.Column("screener_a", sa.String(50), nullable=False),
        sa.Column("screener_b", sa.String(50), nullable=False),
        sa.Column("disagreement_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("resolved_decision", sa.String(50), nullable=True),
        sa.Column("resolved_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "registro_id", name="uq_conflict_review_registro"),
    )

    op.execute("ALTER TABLE conflicts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE conflicts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_conflicts ON conflicts "
        "USING (org_id::text = current_setting('app.current_org', true)) "
        "WITH CHECK (org_id::text = current_setting('app.current_org', true))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON conflicts TO prismai_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_conflicts ON conflicts")
    op.drop_table("conflicts")

    op.drop_constraint("uq_decision_review_registro_screener", "decisions", type_="unique")
    op.create_unique_constraint("uq_decision_review_registro", "decisions", ["review_id", "registro_id"])
    op.drop_column("decisions", "screener")
