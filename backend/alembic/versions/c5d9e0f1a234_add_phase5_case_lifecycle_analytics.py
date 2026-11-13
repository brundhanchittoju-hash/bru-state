"""add_phase5_case_lifecycle_analytics

Revision ID: c5d9e0f1a234
Revises: b4c8d9e0f123
Create Date: 2026-10-29 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d9e0f1a234'
down_revision: Union[str, None] = 'b4c8d9e0f123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Add fields to audit_cases
    if 'audit_cases' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('audit_cases')]
        with op.batch_alter_table('audit_cases', schema=None) as batch_op:
            if 'planned_start_date' not in columns:
                batch_op.add_column(sa.Column('planned_start_date', sa.Date(), nullable=True))
            if 'due_date' not in columns:
                batch_op.add_column(sa.Column('due_date', sa.Date(), nullable=True))
            if 'sanctioned_amount' not in columns:
                batch_op.add_column(sa.Column('sanctioned_amount', sa.Numeric(14, 2), nullable=True))
            if 'version' not in columns:
                batch_op.add_column(sa.Column('version', sa.Integer(), server_default='1', nullable=False))

    # 2. Create case_versions table
    if 'case_versions' not in existing_tables:
        op.create_table(
            'case_versions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('case_id', sa.String(36), sa.ForeignKey('audit_cases.id'), nullable=False),
            sa.Column('version_number', sa.Integer(), nullable=False),
            sa.Column('reopened_by_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('reopen_reason', sa.Text(), nullable=False),
            sa.Column('snapshot_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_case_versions_case_id', 'case_versions', ['case_id'])
        op.create_index('ix_case_versions_deleted_at', 'case_versions', ['deleted_at'])

    # 3. Create scheduled_events table
    if 'scheduled_events' not in existing_tables:
        op.create_table(
            'scheduled_events',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('event_date', sa.Date(), nullable=False),
            sa.Column('case_id', sa.String(36), sa.ForeignKey('audit_cases.id'), nullable=True),
            sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('event_type', sa.String(50), default='audit_deadline', nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_scheduled_events_event_date', 'scheduled_events', ['event_date'])
        op.create_index('ix_scheduled_events_case_id', 'scheduled_events', ['case_id'])
        op.create_index('ix_scheduled_events_deleted_at', 'scheduled_events', ['deleted_at'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'scheduled_events' in existing_tables:
        op.drop_table('scheduled_events')

    if 'case_versions' in existing_tables:
        op.drop_table('case_versions')

    if 'audit_cases' in existing_tables:
        with op.batch_alter_table('audit_cases', schema=None) as batch_op:
            batch_op.drop_column('version')
            batch_op.drop_column('sanctioned_amount')
            batch_op.drop_column('due_date')
            batch_op.drop_column('planned_start_date')
