"""Create user_backgrounds table

Revision ID: 003
Revises: 002
Create Date: 2025-11-30 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_backgrounds table."""
    op.create_table(
        'user_backgrounds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('software_experience', sa.String(), nullable=False),
        sa.Column('hardware_experience', sa.String(), nullable=False),
        sa.Column('robotics_experience', sa.String(), nullable=False),
        sa.Column('programming_languages', sa.String(), nullable=True),
        sa.Column('learning_goals', sa.String(), nullable=True),
        sa.Column('current_role', sa.String(), nullable=False),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes
    op.create_index('ix_user_backgrounds_id', 'user_backgrounds', ['id'], unique=False)
    op.create_index('ix_user_backgrounds_user_id', 'user_backgrounds', ['user_id'], unique=True)

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_user_backgrounds_user_id',
        'user_backgrounds',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Drop user_backgrounds table."""
    op.drop_constraint('fk_user_backgrounds_user_id', 'user_backgrounds', type_='foreignkey')
    op.drop_index('ix_user_backgrounds_user_id', table_name='user_backgrounds')
    op.drop_index('ix_user_backgrounds_id', table_name='user_backgrounds')
    op.drop_table('user_backgrounds')
