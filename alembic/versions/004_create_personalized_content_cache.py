"""create personalized_content_cache table

Revision ID: 004
Revises: 003
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create personalized_content_cache table
    op.create_table(
        'personalized_content_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('chapter_id', sa.String(), nullable=False),
        sa.Column('cache_key', sa.String(64), nullable=False),
        sa.Column('original_content', sa.Text(), nullable=False),
        sa.Column('personalized_content', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )

    # Create indexes
    op.create_index('ix_personalized_content_cache_id', 'personalized_content_cache', ['id'], unique=False)
    op.create_index('ix_personalized_content_cache_chapter_id', 'personalized_content_cache', ['chapter_id'], unique=False)
    op.create_index('ix_personalized_content_cache_cache_key', 'personalized_content_cache', ['cache_key'], unique=True)
    op.create_index('ix_personalized_content_cache_expires_at', 'personalized_content_cache', ['expires_at'], unique=False)

    # Composite index for cache lookups
    op.create_index('idx_cache_lookup', 'personalized_content_cache', ['chapter_id', 'cache_key'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_cache_lookup', table_name='personalized_content_cache')
    op.drop_index('ix_personalized_content_cache_expires_at', table_name='personalized_content_cache')
    op.drop_index('ix_personalized_content_cache_cache_key', table_name='personalized_content_cache')
    op.drop_index('ix_personalized_content_cache_chapter_id', table_name='personalized_content_cache')
    op.drop_index('ix_personalized_content_cache_id', table_name='personalized_content_cache')

    # Drop table
    op.drop_table('personalized_content_cache')
