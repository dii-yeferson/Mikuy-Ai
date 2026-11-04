"""Private anonymous onboarding drafts, before account creation."""

from alembic import op
import sqlalchemy as sa

revision = "52d8e419a302"
down_revision = "09ee8f0da7a5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "onboarding_drafts",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("onboarding_drafts")
