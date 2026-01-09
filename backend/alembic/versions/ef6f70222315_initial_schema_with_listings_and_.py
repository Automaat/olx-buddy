"""Initial schema with listings and related tables

Revision ID: ef6f70222315
Revises: 
Create Date: 2026-01-09 15:50:28.426897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef6f70222315'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create listings table
    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True, server_default='PLN'),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('condition', sa.String(length=50), nullable=True),
        sa.Column('size', sa.String(length=50), nullable=True),
        sa.Column('views', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('images', sa.JSON(), nullable=True),
        sa.Column('platform_metadata', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('sold_at', sa.DateTime(), nullable=True),
        sa.Column('sale_price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('initial_cost', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id')
    )
    op.create_index(op.f('ix_listings_id'), 'listings', ['id'], unique=False)
    op.create_index(op.f('ix_listings_platform'), 'listings', ['platform'], unique=False)
    op.create_index(op.f('ix_listings_status'), 'listings', ['status'], unique=False)

    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_history_id'), 'price_history', ['id'], unique=False)
    op.create_index(op.f('ix_price_history_listing_id'), 'price_history', ['listing_id'], unique=False)

    # Create competitor_prices table
    op.create_table(
        'competitor_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=True),
        sa.Column('competitor_url', sa.Text(), nullable=True),
        sa.Column('competitor_title', sa.Text(), nullable=True),
        sa.Column('price', sa.DECIMAL(precision=10, scale=2), nullable=True),
        sa.Column('similarity_score', sa.DECIMAL(precision=3, scale=2), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_competitor_prices_id'), 'competitor_prices', ['id'], unique=False)
    op.create_index(op.f('ix_competitor_prices_listing_id'), 'competitor_prices', ['listing_id'], unique=False)

    # Create monitors table
    op.create_table(
        'monitors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=True),
        sa.Column('search_query', sa.Text(), nullable=True),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('notify_telegram', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_monitors_id'), 'monitors', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_monitors_id'), table_name='monitors')
    op.drop_table('monitors')
    op.drop_index(op.f('ix_competitor_prices_listing_id'), table_name='competitor_prices')
    op.drop_index(op.f('ix_competitor_prices_id'), table_name='competitor_prices')
    op.drop_table('competitor_prices')
    op.drop_index(op.f('ix_price_history_listing_id'), table_name='price_history')
    op.drop_index(op.f('ix_price_history_id'), table_name='price_history')
    op.drop_table('price_history')
    op.drop_index(op.f('ix_listings_status'), table_name='listings')
    op.drop_index(op.f('ix_listings_platform'), table_name='listings')
    op.drop_index(op.f('ix_listings_id'), table_name='listings')
    op.drop_table('listings')
