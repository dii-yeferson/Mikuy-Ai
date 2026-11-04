"""Separate coach conversations and threaded community comments."""

import sqlalchemy as sa
from alembic import op

revision = "9e3c7a21b012"
down_revision = "8d2b6f10a901"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delete_after", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.add_column("messages", sa.Column("conversation_id", sa.String(36), nullable=True))
    op.execute(
        "INSERT INTO conversations (id, user_id, title, created_at, updated_at) SELECT user_id, user_id, 'Conversación anterior', MIN(created_at), MAX(created_at) FROM messages GROUP BY user_id"
    )
    op.execute("UPDATE messages SET conversation_id = user_id")
    op.alter_column("messages", "conversation_id", nullable=False)
    op.create_foreign_key(
        "fk_messages_conversation",
        "messages",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.add_column("post_comments", sa.Column("parent_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_comment_parent",
        "post_comments",
        "post_comments",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_post_comments_parent_id", "post_comments", ["parent_id"])


def downgrade():
    op.drop_column("post_comments", "parent_id")
    op.drop_column("messages", "conversation_id")
    op.drop_table("conversations")
