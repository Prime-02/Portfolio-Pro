"""add column to portfolio project  table

Revision ID: 3ce24933573d
Revises: fd0304efb730
Create Date: 2025-06-08 15:06:40.907981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ce24933573d'
down_revision: Union[str, None] = 'fd0304efb730'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('portfolio_projects', 'project_description',
               existing_type=sa.VARCHAR(),
               nullable=True,
               schema='portfolio_pro_app')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('portfolio_projects', 'project_description',
               existing_type=sa.VARCHAR(),
               nullable=False,
               schema='portfolio_pro_app')
    # ### end Alembic commands ###
