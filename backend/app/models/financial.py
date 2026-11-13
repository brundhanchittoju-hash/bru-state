from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Vendor(BaseModel):
    __tablename__ = "vendors"

    gstn = Column(String(15), nullable=True, index=True)
    pan = Column(String(10), nullable=True, index=True)
    legal_name = Column(String(255), nullable=False, index=True)
    bank_account_no = Column(String(50), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    is_flagged = Column(Boolean, default=False, nullable=False)

    aliases = relationship("VendorAlias", back_populates="vendor", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="vendor")


class VendorAlias(BaseModel):
    __tablename__ = "vendor_aliases"

    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=False, index=True)
    alias_name = Column(String(255), nullable=False, index=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    status = Column(String(50), default="confirmed", nullable=False)  # confirmed, pending_review, rejected

    vendor = relationship("Vendor", back_populates="aliases")


class Transaction(BaseModel):
    __tablename__ = "transactions"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    voucher_no = Column(String(100), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    debit = Column(Numeric(14, 2), nullable=True)
    credit = Column(Numeric(14, 2), nullable=True)
    balance = Column(Numeric(14, 2), nullable=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=True, index=True)
    scheme_name = Column(String(100), nullable=False, index=True)
    payment_mode = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    source_document_id = Column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    row_number = Column(Integer, nullable=True)

    case = relationship("AuditCase", back_populates="transactions")
    vendor = relationship("Vendor", back_populates="transactions")
    source_document = relationship("Document")


class FinancialRecord(BaseModel):
    __tablename__ = "financial_records"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    vendor_id = Column(String(36), ForeignKey("vendors.id"), nullable=True, index=True)
    record_type = Column(String(50), nullable=False, index=True)  # bill, voucher, ledger_entry, bank_debit, cash_book_entry, sanction, work_order, tender, measurement_book, completion_certificate, utilization_certificate
    document_number = Column(String(100), nullable=True, index=True)
    date = Column(Date, nullable=True, index=True)
    base_amount = Column(Numeric(14, 2), nullable=True)
    tax_amount = Column(Numeric(14, 2), nullable=True)
    total_amount = Column(Numeric(14, 2), nullable=False)
    payment_reference = Column(String(100), nullable=True, index=True)
    cheque_number = Column(String(50), nullable=True)
    source_document_id = Column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    source_page = Column(Integer, nullable=True)
    source_field_ids = Column(Text, nullable=True)
    source_row = Column(Integer, nullable=True)
    raw_data_json = Column(Text, nullable=True)

    case = relationship("AuditCase", back_populates="financial_records")
    vendor = relationship("Vendor")
    source_document = relationship("Document")
    outgoing_links = relationship("RecordLink", foreign_keys="RecordLink.source_record_id", back_populates="source_record", cascade="all, delete-orphan")
    incoming_links = relationship("RecordLink", foreign_keys="RecordLink.target_record_id", back_populates="target_record", cascade="all, delete-orphan")


class RecordLink(BaseModel):
    __tablename__ = "record_links"

    case_id = Column(String(36), ForeignKey("audit_cases.id"), nullable=False, index=True)
    source_record_id = Column(String(36), ForeignKey("financial_records.id"), nullable=False, index=True)
    target_record_id = Column(String(36), ForeignKey("financial_records.id"), nullable=False, index=True)
    link_type = Column(String(50), nullable=False, index=True)  # bill_to_voucher, voucher_to_ledger, voucher_to_bank, etc.
    match_method = Column(String(50), nullable=False)  # explicit_reference, vendor_amount_date, fuzzy
    confidence = Column(Float, default=1.0, nullable=False)
    metadata_json = Column(Text, nullable=True)

    case = relationship("AuditCase", back_populates="record_links")
    source_record = relationship("FinancialRecord", foreign_keys=[source_record_id], back_populates="outgoing_links")
    target_record = relationship("FinancialRecord", foreign_keys=[target_record_id], back_populates="incoming_links")
