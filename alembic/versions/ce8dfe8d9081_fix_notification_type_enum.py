"""fix_notification_type_enum

Revision ID: ce8dfe8d9081
Revises: 937e3b0cec54
Create Date: 2025-06-11 22:20:24.098085

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ce8dfe8d9081"
down_revision: Union[str, None] = "937e3b0cec54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # 1. First convert enum column to text
    op.alter_column(
        "notifications",
        "notification_type",
        type_=sa.Text(),
        postgresql_using="notification_type::text",
    )

    # 2. Drop the old enum type if it exists
    op.execute("DROP TYPE IF EXISTS portfolio_pro_app.notificationtype")

    # 3. Create the new enum type
    notification_type = postgresql.ENUM(
        "TYPE1",
        "TYPE2",
        "TYPE3",  # Replace with your actual enum values
        name="notificationtype",
        schema="portfolio_pro_app",
    )
    notification_type.create(op.get_bind())

    # 4. Convert back to the new enum type
    op.alter_column(
        "notifications",
        "notification_type",
        type_=notification_type,
        postgresql_using="notification_type::portfolio_pro_app.notificationtype",
    )


def downgrade():
    # Reverse the process for downgrade
    op.alter_column(
        "notifications",
        "notification_type",
        type_=sa.Text(),
        postgresql_using="notification_type::text",
    )

    op.execute("DROP TYPE IF EXISTS portfolio_pro_app.notificationtype")

    # Recreate the old enum type if needed
    old_notification_type = postgresql.ENUM(
        "OLD_TYPE1",
        "OLD_TYPE2",  # Replace with your original enum values
        name="notificationtype",
        schema="portfolio_pro_app",
    )
    old_notification_type.create(op.get_bind())

    op.alter_column(
        "notifications",
        "notification_type",
        type_=old_notification_type,
        postgresql_using="notification_type::portfolio_pro_app.notificationtype",
    )
