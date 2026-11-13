"""add_phase2_document_pipeline_fields

Revision ID: 250e05d8e901
Revises: c7998c7729df
Create Date: 2026-10-28 16:44:48.690465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '250e05d8e901'
down_revision: Union[str, None] = 'c7998c7729df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # audit_cases
    existing_case_cols = {c['name'] for c in inspector.get_columns('audit_cases')}
    with op.batch_alter_table('audit_cases', schema=None) as batch_op:
        if 'district' not in existing_case_cols:
            batch_op.add_column(sa.Column('district', sa.String(length=100), nullable=True))
            batch_op.create_index(batch_op.f('ix_audit_cases_district'), ['district'], unique=False)
        if 'taluk' not in existing_case_cols:
            batch_op.add_column(sa.Column('taluk', sa.String(length=100), nullable=True))
            batch_op.create_index(batch_op.f('ix_audit_cases_taluk'), ['taluk'], unique=False)
        if 'gram_panchayat' not in existing_case_cols:
            batch_op.add_column(sa.Column('gram_panchayat', sa.String(length=150), nullable=True))
        if 'scheme_name' not in existing_case_cols:
            batch_op.add_column(sa.Column('scheme_name', sa.String(length=100), nullable=True))
            batch_op.create_index(batch_op.f('ix_audit_cases_scheme_name'), ['scheme_name'], unique=False)
        if 'audit_type' not in existing_case_cols:
            batch_op.add_column(sa.Column('audit_type', sa.String(length=50), nullable=False, server_default='Statutory'))
        if 'project_name' not in existing_case_cols:
            batch_op.add_column(sa.Column('project_name', sa.String(length=255), nullable=True))
        if 'estimated_cost' not in existing_case_cols:
            batch_op.add_column(sa.Column('estimated_cost', sa.Numeric(precision=14, scale=2), nullable=True))
        if 'actual_expenditure' not in existing_case_cols:
            batch_op.add_column(sa.Column('actual_expenditure', sa.Numeric(precision=14, scale=2), nullable=True))
        if 'priority' not in existing_case_cols:
            batch_op.add_column(sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'))
            batch_op.create_index(batch_op.f('ix_audit_cases_priority'), ['priority'], unique=False)
        if 'remarks' not in existing_case_cols:
            batch_op.add_column(sa.Column('remarks', sa.Text(), nullable=True))

    # document_annotations
    existing_annot_cols = {c['name'] for c in inspector.get_columns('document_annotations')}
    with op.batch_alter_table('document_annotations', schema=None) as batch_op:
        if 'finding_id' not in existing_annot_cols:
            batch_op.add_column(sa.Column('finding_id', sa.String(length=36), nullable=True))
            batch_op.create_index(batch_op.f('ix_document_annotations_finding_id'), ['finding_id'], unique=False)

    # document_versions
    existing_ver_cols = {c['name'] for c in inspector.get_columns('document_versions')}
    with op.batch_alter_table('document_versions', schema=None) as batch_op:
        if 'document_type' not in existing_ver_cols:
            batch_op.add_column(sa.Column('document_type', sa.String(length=100), nullable=True))
        if 'classification_confidence' not in existing_ver_cols:
            batch_op.add_column(sa.Column('classification_confidence', sa.Float(), nullable=False, server_default='0.0'))

    # documents
    existing_doc_cols = {c['name'] for c in inspector.get_columns('documents')}
    with op.batch_alter_table('documents', schema=None) as batch_op:
        if 'status' not in existing_doc_cols:
            batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=False, server_default='uploaded'))
            batch_op.create_index(batch_op.f('ix_documents_status'), ['status'], unique=False)
        if 'page_count' not in existing_doc_cols:
            batch_op.add_column(sa.Column('page_count', sa.Integer(), nullable=False, server_default='0'))
        if 'current_version' not in existing_doc_cols:
            batch_op.add_column(sa.Column('current_version', sa.Integer(), nullable=False, server_default='1'))
        if 'processing_error' not in existing_doc_cols:
            batch_op.add_column(sa.Column('processing_error', sa.Text(), nullable=True))
        if 'classification_confidence' not in existing_doc_cols:
            batch_op.add_column(sa.Column('classification_confidence', sa.Float(), nullable=False, server_default='0.0'))
        if 'classification_keywords' not in existing_doc_cols:
            batch_op.add_column(sa.Column('classification_keywords', sa.Text(), nullable=True))
        if 'extractor_used' not in existing_doc_cols:
            batch_op.add_column(sa.Column('extractor_used', sa.String(length=50), nullable=True))
        if 'document_date' not in existing_doc_cols:
            batch_op.add_column(sa.Column('document_date', sa.DateTime(timezone=True), nullable=True))

    # extracted_fields
    existing_field_cols = {c['name'] for c in inspector.get_columns('extracted_fields')}
    with op.batch_alter_table('extracted_fields', schema=None) as batch_op:
        if 'validation_status' not in existing_field_cols:
            batch_op.add_column(sa.Column('validation_status', sa.String(length=20), nullable=False, server_default='not_checked'))
        if 'validation_message' not in existing_field_cols:
            batch_op.add_column(sa.Column('validation_message', sa.Text(), nullable=True))

    # transactions
    existing_txn_cols = {c['name'] for c in inspector.get_columns('transactions')}
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        if 'debit' not in existing_txn_cols:
            batch_op.add_column(sa.Column('debit', sa.Numeric(precision=14, scale=2), nullable=True))
        if 'credit' not in existing_txn_cols:
            batch_op.add_column(sa.Column('credit', sa.Numeric(precision=14, scale=2), nullable=True))
        if 'balance' not in existing_txn_cols:
            batch_op.add_column(sa.Column('balance', sa.Numeric(precision=14, scale=2), nullable=True))
        if 'source_document_id' not in existing_txn_cols:
            batch_op.add_column(sa.Column('source_document_id', sa.String(length=36), nullable=True))
            batch_op.create_index(batch_op.f('ix_transactions_source_document_id'), ['source_document_id'], unique=False)
            batch_op.create_foreign_key('fk_transactions_source_document_id', 'documents', ['source_document_id'], ['id'])
        if 'row_number' not in existing_txn_cols:
            batch_op.add_column(sa.Column('row_number', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_transactions_source_document_id'))
        batch_op.drop_column('row_number')
        batch_op.drop_column('source_document_id')
        batch_op.drop_column('balance')
        batch_op.drop_column('credit')
        batch_op.drop_column('debit')

    with op.batch_alter_table('extracted_fields', schema=None) as batch_op:
        batch_op.drop_column('validation_message')
        batch_op.drop_column('validation_status')

    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_status'))
        batch_op.drop_column('document_date')
        batch_op.drop_column('extractor_used')
        batch_op.drop_column('classification_keywords')
        batch_op.drop_column('classification_confidence')
        batch_op.drop_column('processing_error')
        batch_op.drop_column('current_version')
        batch_op.drop_column('page_count')
        batch_op.drop_column('status')

    with op.batch_alter_table('document_versions', schema=None) as batch_op:
        batch_op.drop_column('classification_confidence')
        batch_op.drop_column('document_type')

    with op.batch_alter_table('document_annotations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_document_annotations_finding_id'))
        batch_op.drop_column('finding_id')

    with op.batch_alter_table('audit_cases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_cases_taluk'))
        batch_op.drop_index(batch_op.f('ix_audit_cases_scheme_name'))
        batch_op.drop_index(batch_op.f('ix_audit_cases_priority'))
        batch_op.drop_index(batch_op.f('ix_audit_cases_district'))
        batch_op.drop_column('remarks')
        batch_op.drop_column('priority')
        batch_op.drop_column('actual_expenditure')
        batch_op.drop_column('estimated_cost')
        batch_op.drop_column('project_name')
        batch_op.drop_column('audit_type')
        batch_op.drop_column('scheme_name')
        batch_op.drop_column('gram_panchayat')
        batch_op.drop_column('taluk')
        batch_op.drop_column('district')

    # ### end Alembic commands ###
