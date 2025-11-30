"""create translation_cache table

Revision ID: 005
Revises: 004
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create translation_cache table
    op.create_table(
        'translation_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('chapter_id', sa.String(), nullable=False),
        sa.Column('cache_key', sa.String(64), nullable=False),
        sa.Column('source_language', sa.String(50), nullable=False, server_default='english'),
        sa.Column('target_language', sa.String(50), nullable=False, server_default='urdu'),
        sa.Column('original_content', sa.Text(), nullable=False),
        sa.Column('translated_content', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
    )

    # Create indexes
    op.create_index('ix_translation_cache_id', 'translation_cache', ['id'], unique=False)
    op.create_index('ix_translation_cache_chapter_id', 'translation_cache', ['chapter_id'], unique=False)
    op.create_index('ix_translation_cache_cache_key', 'translation_cache', ['cache_key'], unique=True)
    op.create_index('ix_translation_cache_expires_at', 'translation_cache', ['expires_at'], unique=False)

    # Composite index for cache lookups
    op.create_index('idx_translation_cache_lookup', 'translation_cache', ['chapter_id', 'cache_key'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_translation_cache_lookup', table_name='translation_cache')
    op.drop_index('ix_translation_cache_expires_at', table_name='translation_cache')
    op.drop_index('ix_translation_cache_cache_key', table_name='translation_cache')
    op.drop_index('ix_translation_cache_chapter_id', table_name='translation_cache')
    op.drop_index('ix_translation_cache_id', table_name='translation_cache')

    # Drop table
    op.drop_table('translation_cache')
