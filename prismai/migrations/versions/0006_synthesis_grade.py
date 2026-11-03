"""Add syntheses, grade_assessments tables + synthesis_config column on protocols

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES_WITH_RLS = ["syntheses", "grade_assessments"]


def upgrade() -> None:
    op.add_column("protocols", sa.Column("synthesis_config", sa.JSON(), nullable=True))

    op.create_table(
        "syntheses",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("outcome_key", sa.String(255), nullable=False),
        sa.Column("measure", sa.String(50), nullable=False),
        sa.Column("model", sa.String(50), nullable=False, server_default="random"),
        sa.Column("k_studies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_participants", sa.Integer(), nullable=True),
        sa.Column("pooled_effect", sa.Float(), nullable=True),
        sa.Column("se", sa.Float(), nullable=True),
        sa.Column("ci_low", sa.Float(), nullable=True),
        sa.Column("ci_high", sa.Float(), nullable=True),
        sa.Column("z", sa.Float(), nullable=True),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("tau2", sa.Float(), nullable=True),
        sa.Column("q", sa.Float(), nullable=True),
        sa.Column("q_p", sa.Float(), nullable=True),
        sa.Column("i2", sa.Float(), nullable=True),
        sa.Column("prediction_low", sa.Float(), nullable=True),
        sa.Column("prediction_high", sa.Float(), nullable=True),
        sa.Column("egger_intercept", sa.Float(), nullable=True),
        sa.Column("egger_p", sa.Float(), nullable=True),
        sa.Column("study_effects", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("unmapped", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("degradado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alertas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "outcome_key", name="uq_synthesis_review_outcome"),
    )

    op.create_table(
        "grade_assessments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("review_id", sa.UUID(), sa.ForeignKey("reviews.id"), nullable=False),
        sa.Column("outcome_key", sa.String(255), nullable=False),
        sa.Column("starting_certainty", sa.String(50), nullable=False, server_default="high"),
        sa.Column("domain_results", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("final_certainty", sa.String(50), nullable=False),
        sa.Column("k_studies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_participants", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("degradado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alertas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("review_id", "outcome_key", name="uq_grade_review_outcome"),
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
    op.drop_column("protocols", "synthesis_config")
