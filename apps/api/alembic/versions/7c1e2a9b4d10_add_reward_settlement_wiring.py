"""add participant wallets, task rewards, and settlement errors

Revision ID: 7c1e2a9b4d10
Revises: 555947f53594
Create Date: 2026-09-26 17:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c1e2a9b4d10"
down_revision: Union[str, Sequence[str], None] = "555947f53594"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("participants", sa.Column("wallet_address", sa.String(length=42), nullable=True))
    op.add_column(
        "tasks", sa.Column("reward_amount", sa.Numeric(precision=24, scale=8), nullable=True)
    )
    op.add_column("reward_settlements", sa.Column("last_error", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_reward_settlement_assignment", "reward_settlements", ["assignment_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_reward_settlement_assignment", "reward_settlements", type_="unique")
    op.drop_column("reward_settlements", "last_error")
    op.drop_column("tasks", "reward_amount")
    op.drop_column("participants", "wallet_address")
