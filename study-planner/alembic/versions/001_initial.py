"""Create users and assignments."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("role IN ('student', 'admin')", name="ck_users_role"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("subject", sa.String(length=80), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('planned', 'in_progress', 'done')", name="ck_assignments_status"),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_assignments_priority"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_assignments_owner_id", "assignments", ["owner_id"], unique=False)
    op.create_index("ix_assignments_due_date", "assignments", ["due_date"], unique=False)
    op.create_index("ix_assignments_owner_due_date", "assignments", ["owner_id", "due_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assignments_owner_due_date", table_name="assignments")
    op.drop_index("ix_assignments_due_date", table_name="assignments")
    op.drop_index("ix_assignments_owner_id", table_name="assignments")
    op.drop_table("assignments")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
