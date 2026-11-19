"""Create chat_feedback table for AgentOps feedback loop

Revision ID: e7f8a9b0c1d2
Revises: a1b2c3d4e5f6
Create Date: 2026-10-31 07:18:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chat_feedback',
        sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key - UUID'),
        sa.Column('session_id', sa.UUID(), nullable=False, comment='Session UUID associated with the feedback'),
        sa.Column('message_id', sa.UUID(), nullable=True, comment='Optional UUID of the specific message being evaluated'),
        sa.Column('rating', sa.Integer(), nullable=False, comment='1 for thumbs up, -1 for thumbs down'),
        sa.Column('comment', sa.Text(), nullable=True, comment='Optional user comment'),
        sa.Column('corrected_mood', sa.String(length=50), nullable=True, comment='User-corrected mood label'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Timestamp when feedback was submitted'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )

    op.create_index(op.f('ix_chat_feedback_id'), 'chat_feedback', ['id'], unique=True)
    op.create_index(op.f('ix_chat_feedback_session_id'), 'chat_feedback', ['session_id'], unique=False)
    op.create_index(op.f('ix_chat_feedback_message_id'), 'chat_feedback', ['message_id'], unique=False)
    op.create_index(op.f('ix_chat_feedback_created_at'), 'chat_feedback', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chat_feedback_created_at'), table_name='chat_feedback')
    op.drop_index(op.f('ix_chat_feedback_message_id'), table_name='chat_feedback')
    op.drop_index(op.f('ix_chat_feedback_session_id'), table_name='chat_feedback')
    op.drop_index(op.f('ix_chat_feedback_id'), table_name='chat_feedback')
    op.drop_table('chat_feedback')
