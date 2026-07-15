"""Initial PayLink schema."""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    from app.db.base import Base
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from app.db.base import Base
    Base.metadata.drop_all(bind=bind)

