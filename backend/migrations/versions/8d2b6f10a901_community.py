"""Persistent communities, memberships, reactions and comments."""

from alembic import op
import sqlalchemy as sa

revision = "8d2b6f10a901"
down_revision = "7c1a9e2b4d10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "community_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_community_groups_owner_id", "community_groups", ["owner_id"])
    op.create_table(
        "group_members",
        sa.Column(
            "group_id",
            sa.String(36),
            sa.ForeignKey("community_groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.add_column("entries", sa.Column("group_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_entries_group", "entries", "community_groups", ["group_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_entries_group_id", "entries", ["group_id"])
    op.create_table(
        "post_reactions",
        sa.Column(
            "post_id",
            sa.String(36),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
    )
    op.create_table(
        "post_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "post_id",
            sa.String(36),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("text", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_post_comments_post_id", "post_comments", ["post_id"])
    op.create_index("ix_post_comments_user_id", "post_comments", ["user_id"])


def downgrade():
    op.drop_table("post_comments")
    op.drop_table("post_reactions")
    op.drop_index("ix_entries_group_id", table_name="entries")
    op.drop_constraint("fk_entries_group", "entries", type_="foreignkey")
    op.drop_column("entries", "group_id")
    op.drop_table("group_members")
    op.drop_table("community_groups")
