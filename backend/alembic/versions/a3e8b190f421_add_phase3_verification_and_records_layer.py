"""add_phase3_verification_and_records_layer

Revision ID: a3e8b190f421
Revises: 250e05d8e901
Create Date: 2026-10-28 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3e8b190f421'
down_revision: Union[str, None] = '250e05d8e901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Create financial_records
    if 'financial_records' not in existing_tables:
        op.create_table(
            'financial_records',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('case_id', sa.String(length=36), sa.ForeignKey('audit_cases.id'), nullable=False),
            sa.Column('vendor_id', sa.String(length=36), sa.ForeignKey('vendors.id'), nullable=True),
            sa.Column('record_type', sa.String(length=50), nullable=False),
            sa.Column('document_number', sa.String(length=100), nullable=True),
            sa.Column('date', sa.Date(), nullable=True),
            sa.Column('base_amount', sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column('tax_amount', sa.Numeric(precision=14, scale=2), nullable=True),
            sa.Column('total_amount', sa.Numeric(precision=14, scale=2), nullable=False),
            sa.Column('payment_reference', sa.String(length=100), nullable=True),
            sa.Column('cheque_number', sa.String(length=50), nullable=True),
            sa.Column('source_document_id', sa.String(length=36), sa.ForeignKey('documents.id'), nullable=True),
            sa.Column('source_page', sa.Integer(), nullable=True),
            sa.Column('source_field_ids', sa.Text(), nullable=True),
            sa.Column('source_row', sa.Integer(), nullable=True),
            sa.Column('raw_data_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        with op.batch_alter_table('financial_records', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_financial_records_case_id'), ['case_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_financial_records_vendor_id'), ['vendor_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_financial_records_record_type'), ['record_type'], unique=False)
            batch_op.create_index(batch_op.f('ix_financial_records_document_number'), ['document_number'], unique=False)
            batch_op.create_index(batch_op.f('ix_financial_records_date'), ['date'], unique=False)
            batch_op.create_index(batch_op.f('ix_financial_records_payment_reference'), ['payment_reference'], unique=False)
            batch_op.create_index(batch_op.f('ix_financial_records_source_document_id'), ['source_document_id'], unique=False)

    # 2. Create record_links
    if 'record_links' not in existing_tables:
        op.create_table(
            'record_links',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('case_id', sa.String(length=36), sa.ForeignKey('audit_cases.id'), nullable=False),
            sa.Column('source_record_id', sa.String(length=36), sa.ForeignKey('financial_records.id'), nullable=False),
            sa.Column('target_record_id', sa.String(length=36), sa.ForeignKey('financial_records.id'), nullable=False),
            sa.Column('link_type', sa.String(length=50), nullable=False),
            sa.Column('match_method', sa.String(length=50), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('metadata_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        with op.batch_alter_table('record_links', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_record_links_case_id'), ['case_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_record_links_source_record_id'), ['source_record_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_record_links_target_record_id'), ['target_record_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_record_links_link_type'), ['link_type'], unique=False)

    # 3. vendor_aliases status
    if 'vendor_aliases' in existing_tables:
        existing_va_cols = {c['name'] for c in inspector.get_columns('vendor_aliases')}
        with op.batch_alter_table('vendor_aliases', schema=None) as batch_op:
            if 'status' not in existing_va_cols:
                batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=False, server_default='confirmed'))

    # 4. findings extensions
    if 'findings' in existing_tables:
        existing_finding_cols = {c['name'] for c in inspector.get_columns('findings')}
        with op.batch_alter_table('findings', schema=None) as batch_op:
            if 'finding_number' not in existing_finding_cols:
                batch_op.add_column(sa.Column('finding_number', sa.String(length=50), nullable=True))
                batch_op.create_index(batch_op.f('ix_findings_finding_number'), ['finding_number'], unique=False)
            if 'fingerprint' not in existing_finding_cols:
                batch_op.add_column(sa.Column('fingerprint', sa.String(length=64), nullable=True))
                batch_op.create_index(batch_op.f('ix_findings_fingerprint'), ['fingerprint'], unique=False)
            if 'category' not in existing_finding_cols:
                batch_op.add_column(sa.Column('category', sa.String(length=100), nullable=False, server_default='financial'))
                batch_op.create_index(batch_op.f('ix_findings_category'), ['category'], unique=False)
            if 'reason' not in existing_finding_cols:
                batch_op.add_column(sa.Column('reason', sa.Text(), nullable=True))
            if 'calculation' not in existing_finding_cols:
                batch_op.add_column(sa.Column('calculation', sa.Text(), nullable=True))
            if 'amount_at_risk' not in existing_finding_cols:
                batch_op.add_column(sa.Column('amount_at_risk', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0.0'))
            if 'confidence' not in existing_finding_cols:
                batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=False, server_default='100.0'))
            if 'inputs_used_json' not in existing_finding_cols:
                batch_op.add_column(sa.Column('inputs_used_json', sa.Text(), nullable=True))
            if 'thresholds_used_json' not in existing_finding_cols:
                batch_op.add_column(sa.Column('thresholds_used_json', sa.Text(), nullable=True))
            if 'evidence_json' not in existing_finding_cols:
                batch_op.add_column(sa.Column('evidence_json', sa.Text(), nullable=True))
            if 'data_changed_since_review' not in existing_finding_cols:
                batch_op.add_column(sa.Column('data_changed_since_review', sa.Boolean(), nullable=False, server_default=sa.false()))
            if 'assigned_auditor_id' not in existing_finding_cols:
                batch_op.add_column(sa.Column('assigned_auditor_id', sa.String(length=36), nullable=True))
            if 'auto_resolved_at' not in existing_finding_cols:
                batch_op.add_column(sa.Column('auto_resolved_at', sa.DateTime(timezone=True), nullable=True))

    # 5. rule_runs extensions
    if 'rule_runs' in existing_tables:
        existing_run_cols = {c['name'] for c in inspector.get_columns('rule_runs')}
        with op.batch_alter_table('rule_runs', schema=None) as batch_op:
            if 'thresholds_snapshot_json' not in existing_run_cols:
                batch_op.add_column(sa.Column('thresholds_snapshot_json', sa.Text(), nullable=True))
            if 'execution_summary_json' not in existing_run_cols:
                batch_op.add_column(sa.Column('execution_summary_json', sa.Text(), nullable=True))
            if 'duration_ms' not in existing_run_cols:
                batch_op.add_column(sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'))

    # 6. rule_settings_history extensions
    if 'rule_settings_history' in existing_tables:
        existing_hist_cols = {c['name'] for c in inspector.get_columns('rule_settings_history')}
        with op.batch_alter_table('rule_settings_history', schema=None) as batch_op:
            if 'reason' not in existing_hist_cols:
                batch_op.add_column(sa.Column('reason', sa.Text(), nullable=True))


def downgrade() -> None:
    # Downgrade drops
    op.drop_table('record_links')
    op.drop_table('financial_records')
