"""add_phase4_findings_review_extensions

Revision ID: b4c8d9e0f123
Revises: a3e8b190f421
Create Date: 2026-10-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c8d9e0f123'
down_revision: Union[str, None] = 'a3e8b190f421'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Update finding_reviews with previous_status and new_status
    if 'finding_reviews' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('finding_reviews')]
        with op.batch_alter_table('finding_reviews', schema=None) as batch_op:
            if 'previous_status' not in columns:
                batch_op.add_column(sa.Column('previous_status', sa.String(length=50), nullable=True))
            if 'new_status' not in columns:
                batch_op.add_column(sa.Column('new_status', sa.String(length=50), nullable=True))

    # 2. Create finding_notes
    if 'finding_notes' not in existing_tables:
        op.create_table(
            'finding_notes',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('finding_id', sa.String(length=36), sa.ForeignKey('findings.id'), nullable=False),
            sa.Column('author_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('parent_id', sa.String(length=36), sa.ForeignKey('finding_notes.id'), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        with op.batch_alter_table('finding_notes', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_finding_notes_finding_id'), ['finding_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_finding_notes_author_id'), ['author_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_finding_notes_parent_id'), ['parent_id'], unique=False)

    # 3. Create finding_clarifications
    if 'finding_clarifications' not in existing_tables:
        op.create_table(
            'finding_clarifications',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('finding_id', sa.String(length=36), sa.ForeignKey('findings.id'), nullable=False),
            sa.Column('requested_by_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('question', sa.Text(), nullable=False),
            sa.Column('responded_by_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('response', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
            sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        with op.batch_alter_table('finding_clarifications', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_finding_clarifications_finding_id'), ['finding_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_finding_clarifications_requested_by_id'), ['requested_by_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_finding_clarifications_responded_by_id'), ['responded_by_id'], unique=False)

    # 4. Create saved_filters
    if 'saved_filters' not in existing_tables:
        op.create_table(
            'saved_filters',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('entity_type', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('filter_json', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        with op.batch_alter_table('saved_filters', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_saved_filters_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_saved_filters_entity_type'), ['entity_type'], unique=False)

    # 5. Create user_preferences
    if 'user_preferences' not in existing_tables:
        op.create_table(
            'user_preferences',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('preference_key', sa.String(length=100), nullable=False),
            sa.Column('preference_value', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        with op.batch_alter_table('user_preferences', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_user_preferences_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_user_preferences_preference_key'), ['preference_key'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'user_preferences' in existing_tables:
        op.drop_table('user_preferences')
    if 'saved_filters' in existing_tables:
        op.drop_table('saved_filters')
    if 'finding_clarifications' in existing_tables:
        op.drop_table('finding_clarifications')
    if 'finding_notes' in existing_tables:
        op.drop_table('finding_notes')

    if 'finding_reviews' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('finding_reviews')]
        with op.batch_alter_table('finding_reviews', schema=None) as batch_op:
            if 'new_status' in columns:
                batch_op.drop_column('new_status')
            if 'previous_status' in columns:
                batch_op.drop_column('previous_status')

