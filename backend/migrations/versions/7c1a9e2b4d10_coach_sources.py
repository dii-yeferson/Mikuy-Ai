"""Coach answers keep their cited sources and answer mode."""

from alembic import op
import sqlalchemy as sa

revision = "7c1a9e2b4d10"
down_revision = "52d8e419a302"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("messages", sa.Column("sources", sa.JSON(), nullable=True))
    op.add_column("messages", sa.Column("mode", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("messages", "mode")
    op.drop_column("messages", "sources")
