"""Default de schema_version passa a cochrane-default-v2.

Não reescreve extrações já gravadas.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "extractions",
        "schema_version",
        existing_type=sa.String(100),
        server_default="cochrane-default-v2",
    )


def downgrade() -> None:
    op.alter_column(
        "extractions",
        "schema_version",
        existing_type=sa.String(100),
        server_default="cochrane-default-v1",
    )
