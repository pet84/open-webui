"""add last_read_at to chat

Revision ID: b7c8d9e0f1a2
Revises: d4e5f6a7b8c9
Create Date: 2026-04-01 04:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1a2'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def _chat_column_names(conn) -> set[str]:
    insp = sa.inspect(conn)
    return {c['name'] for c in insp.get_columns('chat')}


def upgrade():
    conn = op.get_bind()
    cols = _chat_column_names(conn)
    if 'last_read_at' not in cols:
        op.add_column('chat', sa.Column('last_read_at', sa.BigInteger(), nullable=True))
    # Mark existing chats as read where still null (fresh or existing column)
    op.execute('UPDATE chat SET last_read_at = updated_at WHERE last_read_at IS NULL')


def downgrade():
    conn = op.get_bind()
    cols = _chat_column_names(conn)
    if 'last_read_at' in cols:
        op.drop_column('chat', 'last_read_at')
