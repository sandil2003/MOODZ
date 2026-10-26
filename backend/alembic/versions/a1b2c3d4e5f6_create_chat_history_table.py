"""Create chat_history table

Revision ID: a1b2c3d4e5f6
Revises: 9f8a6bc98432
Create Date: 2025-12-20 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9f8a6bc98432'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create chat_history table
    op.create_table('chat_history',
        sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key - UUID'),
        sa.Column('user_id', sa.UUID(), nullable=False, comment='User who sent/received this message'),
        sa.Column('session_id', sa.UUID(), nullable=False, comment='Groups messages into conversations'),
        sa.Column('role', sa.String(length=20), nullable=False, comment="Either 'user' or 'assistant'"),
        sa.Column('content', sa.Text(), nullable=False, comment='The actual message text'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, comment='When the message was created'),
        sa.Column('deep_search', sa.Boolean(), nullable=False, comment='Whether deep search was used'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_chat_history_user_id'), 'chat_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_chat_history_session_id'), 'chat_history', ['session_id'], unique=False)
    op.create_index(op.f('ix_chat_history_timestamp'), 'chat_history', ['timestamp'], unique=False)
    op.create_index('idx_user_session', 'chat_history', ['user_id', 'session_id'], unique=False)
    op.create_index('idx_user_timestamp', 'chat_history', ['user_id', 'timestamp'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_user_timestamp', table_name='chat_history')
    op.drop_index('idx_user_session', table_name='chat_history')
    op.drop_index(op.f('ix_chat_history_timestamp'), table_name='chat_history')
    op.drop_index(op.f('ix_chat_history_session_id'), table_name='chat_history')
    op.drop_index(op.f('ix_chat_history_user_id'), table_name='chat_history')
    
    # Drop table
    op.drop_table('chat_history')
