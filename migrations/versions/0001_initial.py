"""Create the complete ORM schema.

The metadata-driven implementation keeps SQLite and PostgreSQL behavior aligned;
custom TypeDecorators select native PostgreSQL types and portable SQLite types.
"""
from alembic import op

from app.models import Base  # imports/registers every ORM model

revision = "0001_initial"
down_revision = None
branch_labels = None

def upgrade() -> None:
    """Create all registered ORM tables in dependency order."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

def downgrade() -> None:
    """Drop all ORM tables in reverse foreign-key dependency order."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
