"""Add secured authentication columns and user_sessions table

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-11-18 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f8a9b0c1d2e3'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    user_columns = [c['name'] for c in insp.get_columns('users')]

    # 1. Add security columns to users table if they don't already exist
    if 'mfa_secret' not in user_columns:
        op.add_column('users', sa.Column('mfa_secret', sa.String(length=64), nullable=True, comment='Base32 TOTP secret key for 2FA'))
    if 'mfa_enabled' not in user_columns:
        op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Whether TOTP 2FA is active'))
    if 'mfa_backup_codes' not in user_columns:
        op.add_column('users', sa.Column('mfa_backup_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb"), comment='Hashed single-use recovery backup codes'))
    if 'failed_login_attempts' not in user_columns:
        op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='Consecutive failed authentication attempts'))
    if 'locked_until' not in user_columns:
        op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True, comment='Account lockout expiration timestamp'))
    if 'password_changed_at' not in user_columns:
        op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='Timestamp of last password change'))

    # 2. Create user_sessions table if it doesn't already exist
    existing_tables = insp.get_table_names()
    if 'user_sessions' not in existing_tables:
        op.create_table(
            'user_sessions',
            sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key - Session UUID'),
            sa.Column('user_id', sa.UUID(), nullable=False, comment='User owning this session'),
            sa.Column('refresh_token_hash', sa.String(length=128), nullable=False, comment='SHA-256 hash of active refresh token'),
            sa.Column('family_id', sa.UUID(), nullable=False, comment='Token family identifier for reuse detection'),
            sa.Column('ip_address', sa.String(length=45), nullable=True, comment='Client IP address'),
            sa.Column('user_agent', sa.Text(), nullable=True, comment='Client User-Agent header'),
            sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Whether session has been explicitly revoked'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='Session creation timestamp'),
            sa.Column('expires_at', sa.DateTime(), nullable=False, comment='Refresh token expiration timestamp'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('id')
        )
        op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
        op.create_index(op.f('ix_user_sessions_family_id'), 'user_sessions', ['family_id'], unique=False)
        op.create_index(op.f('ix_user_sessions_refresh_token_hash'), 'user_sessions', ['refresh_token_hash'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = insp.get_table_names()
    if 'user_sessions' in existing_tables:
        indexes = [idx['name'] for idx in insp.get_indexes('user_sessions')]
        if 'ix_user_sessions_refresh_token_hash' in indexes:
            op.drop_index(op.f('ix_user_sessions_refresh_token_hash'), table_name='user_sessions')
        if 'ix_user_sessions_family_id' in indexes:
            op.drop_index(op.f('ix_user_sessions_family_id'), table_name='user_sessions')
        if 'ix_user_sessions_user_id' in indexes:
            op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
        op.drop_table('user_sessions')

    user_columns = [c['name'] for c in insp.get_columns('users')]
    for col in ['password_changed_at', 'locked_until', 'failed_login_attempts', 'mfa_backup_codes', 'mfa_enabled', 'mfa_secret']:
        if col in user_columns:
            op.drop_column('users', col)
