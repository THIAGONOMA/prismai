"""Enrich records with doi, authors, year, source, title_norm

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("records", sa.Column("doi", sa.String(255), nullable=True))
    op.add_column("records", sa.Column("authors", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("records", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("records", sa.Column("source", sa.String(50), nullable=False, server_default="manual"))
    op.add_column("records", sa.Column("title_norm", sa.Text(), nullable=True))

    op.create_index("ix_records_doi", "records", ["doi"])
    op.create_index(
        "ix_records_review_doi",
        "records",
        ["review_id", "doi"],
        unique=True,
        postgresql_where=sa.text("doi IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_records_review_doi", table_name="records")
    op.drop_index("ix_records_doi", table_name="records")
    op.drop_column("records", "title_norm")
    op.drop_column("records", "source")
    op.drop_column("records", "year")
    op.drop_column("records", "authors")
    op.drop_column("records", "doi")
