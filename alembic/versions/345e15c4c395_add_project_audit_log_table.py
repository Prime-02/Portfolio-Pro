"""add project_audit_log table

Revision ID: 345e15c4c395
Revises: be3e21f67ec6
Create Date: 2025-06-07 17:50:18.517878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '345e15c4c395'
down_revision: Union[str, None] = 'be3e21f67ec6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project_audit_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('project_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['portfolio_pro_app.portfolio_projects.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['portfolio_pro_app.users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='portfolio_pro_app'
    )
    op.create_index('idx_project_audit_action', 'project_audit_logs', ['action'], unique=False, schema='portfolio_pro_app')
    op.create_index('idx_project_audit_project_id', 'project_audit_logs', ['project_id'], unique=False, schema='portfolio_pro_app')
    op.create_index('idx_project_audit_user_id', 'project_audit_logs', ['user_id'], unique=False, schema='portfolio_pro_app')
    op.alter_column('certifications', 'issue_date',
               existing_type=sa.DATE(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               schema='portfolio_pro_app')
    op.alter_column('certifications', 'expiration_date',
               existing_type=sa.DATE(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True,
               schema='portfolio_pro_app')
    op.add_column('portfolio_projects', sa.Column('is_public', sa.Boolean(), nullable=True), schema='portfolio_pro_app')
    op.drop_constraint(op.f('portfolio_projects_user_id_fkey'), 'portfolio_projects', schema='portfolio_pro_app', type_='foreignkey')
    op.drop_column('portfolio_projects', 'user_id', schema='portfolio_pro_app')
    op.add_column('user_project_association', sa.Column('can_edit', sa.Boolean(), nullable=True), schema='portfolio_pro_app')
    op.create_index('idx_user_project_project_id', 'user_project_association', ['project_id'], unique=False, schema='portfolio_pro_app')
    op.create_index('idx_user_project_user_id', 'user_project_association', ['user_id'], unique=False, schema='portfolio_pro_app')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_user_project_user_id', table_name='user_project_association', schema='portfolio_pro_app')
    op.drop_index('idx_user_project_project_id', table_name='user_project_association', schema='portfolio_pro_app')
    op.drop_column('user_project_association', 'can_edit', schema='portfolio_pro_app')
    op.add_column('portfolio_projects', sa.Column('user_id', sa.UUID(), autoincrement=False, nullable=True), schema='portfolio_pro_app')
    op.create_foreign_key(op.f('portfolio_projects_user_id_fkey'), 'portfolio_projects', 'users', ['user_id'], ['id'], source_schema='portfolio_pro_app', referent_schema='portfolio_pro_app')
    op.drop_column('portfolio_projects', 'is_public', schema='portfolio_pro_app')
    op.alter_column('certifications', 'expiration_date',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DATE(),
               existing_nullable=True,
               schema='portfolio_pro_app')
    op.alter_column('certifications', 'issue_date',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DATE(),
               existing_nullable=True,
               schema='portfolio_pro_app')
    op.drop_index('idx_project_audit_user_id', table_name='project_audit_logs', schema='portfolio_pro_app')
    op.drop_index('idx_project_audit_project_id', table_name='project_audit_logs', schema='portfolio_pro_app')
    op.drop_index('idx_project_audit_action', table_name='project_audit_logs', schema='portfolio_pro_app')
    op.drop_table('project_audit_logs', schema='portfolio_pro_app')
    # ### end Alembic commands ###
