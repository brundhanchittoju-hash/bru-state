"""add phase 6 reports generation and verification

Revision ID: d6e0f1a2b345
Revises: c5d9e0f1a234
Create Date: 2026-10-30 12:46:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd6e0f1a2b345'
down_revision = 'c5d9e0f1a234'
branch_labels = None
depends_on = None


def upgrade():
    # Extend reports table
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.add_column(sa.Column('report_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('current_version', sa.Integer(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('approval_comment', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_reports_report_number'), ['report_number'], unique=True)

    # Extend report_versions table
    with op.batch_alter_table('report_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=True, server_default='Draft'))
        batch_op.add_column(sa.Column('file_path', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('file_size_bytes', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('page_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pdf_sha256', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('snapshot_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('includes_demo_watermark', sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column('generated_by_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('approved_by_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('approval_comment', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_report_versions_pdf_sha256'), ['pdf_sha256'], unique=False)


def downgrade():
    with op.batch_alter_table('report_versions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_report_versions_pdf_sha256'))
        batch_op.drop_column('approval_comment')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approved_by_id')
        batch_op.drop_column('generated_by_id')
        batch_op.drop_column('includes_demo_watermark')
        batch_op.drop_column('snapshot_json')
        batch_op.drop_column('pdf_sha256')
        batch_op.drop_column('page_count')
        batch_op.drop_column('file_size_bytes')
        batch_op.drop_column('file_path')
        batch_op.drop_column('status')

    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reports_report_number'))
        batch_op.drop_column('approval_comment')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('current_version')
        batch_op.drop_column('report_number')

