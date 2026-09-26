"""Create the Phase 0 migration baseline.

Revision ID: 0001_phase0_bootstrap
Revises:
"""

revision = "0001_phase0_bootstrap"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Domain tables are introduced in Phase 1.
    pass


def downgrade() -> None:
    pass
