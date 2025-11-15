"""
Structured Metadata Schema Definitions
========================================

Defines the schema for extracted business metadata from different document categories.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class BaseDocumentMetadata(BaseModel):
    """Base metadata common to all documents."""

    # File system metadata
    file_path: str
    file_name: str
    file_type: str
    file_size: int
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    page_count: Optional[int] = None
    author: Optional[str] = None
    title: Optional[str] = None

    # Extraction metadata
    extraction_method: Optional[str] = None  # 'rule_based', 'llm', 'hybrid'
    extraction_confidence: Optional[float] = None  # 0.0 - 1.0
    extracted_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else None,
        }


class InvoiceMetadata(BaseDocumentMetadata):
    """Metadata specific to invoices and receipts."""

    # Invoice identification
    invoice_number: Optional[str] = None
    receipt_number: Optional[str] = None

    # Dates
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None

    # Parties
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_phone: Optional[str] = None
    vendor_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None

    # Financial
    currency: Optional[str] = Field(default="USD")
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    amount_due: Optional[Decimal] = None

    # Payment
    payment_method: Optional[str] = None  # 'credit_card', 'check', 'wire', etc.
    payment_terms: Optional[str] = None  # 'Net 30', 'Due on receipt', etc.
    payment_status: Optional[str] = None  # 'paid', 'unpaid', 'partial', 'overdue'

    # Line items (simplified)
    item_count: Optional[int] = None
    line_items: Optional[List[Dict[str, Any]]] = None  # [{description, quantity, price, total}]

    @validator('total_amount', 'subtotal', 'tax_amount', pre=True)
    def parse_amount(cls, v):
        """Parse amount strings to Decimal."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        if isinstance(v, str):
            # Remove currency symbols and commas
            v = v.replace('$', '').replace(',', '').strip()
            return Decimal(v) if v else None
        return v


class ContractMetadata(BaseDocumentMetadata):
    """Metadata specific to contracts and agreements."""

    # Contract identification
    contract_number: Optional[str] = None
    contract_type: Optional[str] = None  # 'service', 'employment', 'NDA', etc.

    # Parties
    party_a: Optional[str] = None  # Company/organization
    party_b: Optional[str] = None  # Client/contractor/employee
    additional_parties: Optional[List[str]] = None

    # Dates
    execution_date: Optional[date] = None
    effective_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    expiration_date: Optional[date] = None

    # Financial
    contract_value: Optional[Decimal] = None
    currency: Optional[str] = Field(default="USD")
    payment_schedule: Optional[str] = None

    # Terms
    duration_months: Optional[int] = None
    renewal_terms: Optional[str] = None
    termination_clause: Optional[bool] = None
    confidentiality_clause: Optional[bool] = None

    # Status
    status: Optional[str] = None  # 'draft', 'active', 'expired', 'terminated'
    is_signed: Optional[bool] = None
    signatory_names: Optional[List[str]] = None


class ReportMetadata(BaseDocumentMetadata):
    """Metadata specific to reports and analyses."""

    # Report identification
    report_type: Optional[str] = None  # 'financial', 'quarterly', 'annual', 'technical'
    report_number: Optional[str] = None

    # Temporal
    report_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[str] = None  # 'Q1', 'Q2', 'Q3', 'Q4'

    # Organization
    department: Optional[str] = None
    division: Optional[str] = None
    prepared_by: Optional[str] = None
    reviewed_by: Optional[str] = None

    # Financial metrics (if applicable)
    revenue: Optional[Decimal] = None
    expenses: Optional[Decimal] = None
    profit: Optional[Decimal] = None
    growth_rate: Optional[Decimal] = None

    # Classification
    confidentiality_level: Optional[str] = None  # 'public', 'internal', 'confidential'
    distribution_list: Optional[List[str]] = None


class CorrespondenceMetadata(BaseDocumentMetadata):
    """Metadata specific to emails and correspondence."""

    # Identification
    message_id: Optional[str] = None
    subject: Optional[str] = None

    # Parties
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    recipients: Optional[List[str]] = None
    cc_recipients: Optional[List[str]] = None

    # Temporal
    sent_date: Optional[datetime] = None
    received_date: Optional[datetime] = None

    # Content classification
    has_attachments: Optional[bool] = None
    attachment_count: Optional[int] = None
    priority: Optional[str] = None  # 'low', 'normal', 'high', 'urgent'

    # Meeting related
    is_meeting_related: Optional[bool] = None
    meeting_date: Optional[datetime] = None
    meeting_location: Optional[str] = None
    has_action_items: Optional[bool] = None


class ComplianceMetadata(BaseDocumentMetadata):
    """Metadata specific to compliance and regulatory documents."""

    # Identification
    regulation_name: Optional[str] = None
    regulation_number: Optional[str] = None
    compliance_type: Optional[str] = None  # 'GDPR', 'HIPAA', 'SOX', etc.

    # Temporal
    effective_date: Optional[date] = None
    review_date: Optional[date] = None
    next_review_date: Optional[date] = None

    # Status
    compliance_status: Optional[str] = None  # 'compliant', 'non_compliant', 'in_review'
    auditor: Optional[str] = None
    certification_number: Optional[str] = None


# Metadata type registry
METADATA_CLASSES = {
    'invoices': InvoiceMetadata,
    'receipts': InvoiceMetadata,  # Use same as invoices
    'contracts': ContractMetadata,
    'agreements': ContractMetadata,
    'reports': ReportMetadata,
    'correspondence': CorrespondenceMetadata,
    'emails': CorrespondenceMetadata,
    'compliance': ComplianceMetadata,
    'regulatory': ComplianceMetadata,
}


def get_metadata_class(category: str) -> type[BaseDocumentMetadata]:
    """Get the appropriate metadata class for a document category."""
    return METADATA_CLASSES.get(category.lower(), BaseDocumentMetadata)


def create_metadata_instance(category: str, **kwargs) -> BaseDocumentMetadata:
    """Create a metadata instance for the given category."""
    metadata_class = get_metadata_class(category)
    return metadata_class(**kwargs)
