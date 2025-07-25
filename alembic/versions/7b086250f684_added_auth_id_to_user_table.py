"""added auth_id to User table

Revision ID: 7b086250f684
Revises: 15f55777e392
Create Date: 2025-07-03 02:28:51.930960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b086250f684'
down_revision: Union[str, None] = '15f55777e392'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'auth_id',
               existing_type=sa.VARCHAR(),
               nullable=True,
               schema='portfolio_pro_app')
    op.drop_index(op.f('ix_portfolio_pro_app_users_auth_id'), table_name='users', schema='portfolio_pro_app')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_portfolio_pro_app_users_auth_id'), 'users', ['auth_id'], unique=True, schema='portfolio_pro_app')
    op.alter_column('users', 'auth_id',
               existing_type=sa.VARCHAR(),
               nullable=False,
               schema='portfolio_pro_app')
    # ### end Alembic commands ###
