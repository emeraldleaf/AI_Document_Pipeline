"""
Hybrid Metadata Extraction Engine
===================================

Extracts structured business metadata from documents using:
1. Rule-based extraction (fast, reliable for structured formats)
2. LLM-based extraction (flexible, handles variations)
3. Hybrid approach (rules + LLM validation)
"""

import re
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from loguru import logger

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not available, LLM extraction will be disabled")

from metadata_schema import (
    InvoiceMetadata,
    ContractMetadata,
    ReportMetadata,
    CorrespondenceMetadata,
    BaseDocumentMetadata,
    get_metadata_class
)


class RuleBasedExtractor:
    """Rule-based extraction using regex patterns."""

    @staticmethod
    def extract_invoice_metadata(text: str) -> Dict[str, Any]:
        """Extract invoice metadata using regex patterns."""
        metadata = {}

        # Invoice/Receipt number
        invoice_patterns = [
            r'Invoice\s*(?:#|No\.?|Number)?\s*:?\s*([A-Z0-9-]+)',
            r'INV[-_](\d{4}[-_]\d{3,})',
            r'Invoice\s+([A-Z0-9-]+)',
            r'Receipt\s*(?:#|No\.?|Number)?\s*:?\s*([A-Z0-9-]+)',
            r'REC[-_](\d{4}[-\d]+)',
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['invoice_number'] = match.group(1)
                break

        # Dates
        date_patterns = [
            (r'Invoice\s+Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', 'invoice_date'),
            (r'Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', 'invoice_date'),
            (r'Date\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', 'invoice_date'),
            (r'Due\s+Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', 'due_date'),
            (r'Due\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', 'due_date'),
        ]
        for pattern, field_name in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and field_name not in metadata:
                try:
                    date_str = match.group(1)
                    # Try parsing different date formats
                    for fmt in ['%B %d, %Y', '%b %d, %Y', '%m/%d/%Y', '%B %d %Y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt).date()
                            metadata[field_name] = parsed_date.isoformat()
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    logger.debug(f"Failed to parse date '{date_str}': {e}")

        # Total amount
        total_patterns = [
            r'TOTAL\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'Total\s+Amount\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'Amount\s+Due\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'Grand\s+Total\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    metadata['total_amount'] = float(amount_str)
                    break
                except ValueError:
                    pass

        # Subtotal
        subtotal_patterns = [
            r'Sub(?:total|-total)\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'Subtotal\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
        ]
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    metadata['subtotal'] = float(amount_str)
                    break
                except ValueError:
                    pass

        # Tax
        tax_patterns = [
            r'(?:Sales\s+)?Tax\s*(?:\([\d.]+%\))?\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'Tax\s+Amount\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    metadata['tax_amount'] = float(amount_str)
                    break
                except ValueError:
                    pass

        # Vendor/Merchant
        vendor_patterns = [
            r'(?:FROM|MERCHANT|VENDOR)\s*:?\s*\n\s*([^\n]+)',
            r'^([A-Z][a-zA-Z\s&]+(?:Inc|LLC|Corp|Ltd)\.?)\s*$',
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                if len(vendor) > 3 and len(vendor) < 100:
                    metadata['vendor_name'] = vendor
                    break

        # Customer
        customer_patterns = [
            r'(?:TO|BILL TO|CUSTOMER)\s*:?\s*\n\s*([^\n]+)',
        ]
        for pattern in customer_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                customer = match.group(1).strip()
                if len(customer) > 3 and len(customer) < 100:
                    metadata['customer_name'] = customer
                    break

        # Payment terms
        terms_patterns = [
            r'Payment\s+Terms?\s*:?\s*([^\n]+)',
            r'Terms?\s*:?\s*(Net\s+\d+|Due\s+on\s+receipt)',
        ]
        for pattern in terms_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['payment_terms'] = match.group(1).strip()
                break

        # Payment method
        method_patterns = [
            r'Payment\s+Method\s*:?\s*([^\n]+)',
            r'Paid\s+by\s*:?\s*([^\n]+)',
        ]
        for pattern in method_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                method = match.group(1).strip()
                metadata['payment_method'] = method
                break

        return metadata

    @staticmethod
    def extract_contract_metadata(text: str) -> Dict[str, Any]:
        """Extract contract metadata using regex patterns."""
        metadata = {}

        # Contract number
        contract_patterns = [
            r'Contract\s+(?:#|No\.?|Number)\s*:?\s*([A-Z0-9-]+)',
            r'Agreement\s+No\.\s*:?\s*([A-Z0-9-]+)',
        ]
        for pattern in contract_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['contract_number'] = match.group(1)
                break

        # Contract type
        type_patterns = [
            r'(Service\s+Agreement|Employment\s+Contract|Non-Disclosure\s+Agreement|Consulting\s+Agreement)',
        ]
        for pattern in type_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['contract_type'] = match.group(1)
                break

        # Dates
        date_patterns = [
            (r'Effective\s+Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', 'effective_date'),
            (r'Start\s+Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', 'start_date'),
            (r'End\s+Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', 'end_date'),
            (r'Expiration\s+Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', 'expiration_date'),
        ]
        for pattern, field_name in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    for fmt in ['%B %d, %Y', '%b %d, %Y', '%B %d %Y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt).date()
                            metadata[field_name] = parsed_date.isoformat()
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    logger.debug(f"Failed to parse date: {e}")

        # Contract value
        value_patterns = [
            r'Contract\s+Value\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
            r'Total\s+Contract\s+Amount\s*:?\s*\$?\s*([\d,]+\.?\d{0,2})',
        ]
        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    metadata['contract_value'] = float(amount_str)
                    break
                except ValueError:
                    pass

        # Parties
        party_patterns = [
            (r'between\s+([^,\n]+?)\s+(?:and|&)', 'party_a'),
            (r'(?:and|&)\s+([^,\n]+?)\s+(?:hereby|agree)', 'party_b'),
        ]
        for pattern, field_name in party_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                party = match.group(1).strip()
                if len(party) > 3 and len(party) < 100:
                    metadata[field_name] = party

        return metadata

    @staticmethod
    def extract_report_metadata(text: str) -> Dict[str, Any]:
        """Extract report metadata using regex patterns."""
        metadata = {}

        # Report type
        type_patterns = [
            r'(Financial|Quarterly|Annual|Technical|Sales|Marketing)\s+Report',
        ]
        for pattern in type_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata['report_type'] = match.group(1).lower()
                break

        # Fiscal quarter/year
        if match := re.search(r'(Q[1-4])\s+(\d{4})', text):
            metadata['fiscal_quarter'] = match.group(1)
            metadata['fiscal_year'] = int(match.group(2))

        # Fiscal year alone
        if 'fiscal_year' not in metadata:
            if match := re.search(r'FY\s*(\d{4})|Fiscal\s+Year\s+(\d{4})', text, re.IGNORECASE):
                metadata['fiscal_year'] = int(match.group(1) or match.group(2))

        # Department
        if match := re.search(r'Department\s*:?\s*([^\n]+)', text, re.IGNORECASE):
            metadata['department'] = match.group(1).strip()

        # Prepared by
        if match := re.search(r'Prepared\s+by\s*:?\s*([^\n]+)', text, re.IGNORECASE):
            metadata['prepared_by'] = match.group(1).strip()

        # Report date
        if match := re.search(r'Report\s+Date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})', text, re.IGNORECASE):
            try:
                date_str = match.group(1)
                for fmt in ['%B %d, %Y', '%b %d, %Y', '%B %d %Y']:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        metadata['report_date'] = parsed_date.isoformat()
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        return metadata


class LLMExtractor:
    """LLM-based extraction using Ollama."""

    def __init__(self, model: str = "llama3.2:3b"):
        self.model = model
        self.available = OLLAMA_AVAILABLE

    def extract_invoice_metadata(self, text: str) -> Dict[str, Any]:
        """Extract invoice metadata using LLM."""
        if not self.available:
            return {}

        # Truncate text to avoid token limits
        text_sample = text[:3000]

        prompt = f"""Extract structured metadata from this invoice document.

Invoice text:
{text_sample}

Extract the following information and return ONLY valid JSON (no other text):
{{
  "invoice_number": "invoice or receipt number",
  "invoice_date": "date in YYYY-MM-DD format",
  "due_date": "due date in YYYY-MM-DD format or null",
  "vendor_name": "vendor or merchant name",
  "customer_name": "customer name or null",
  "total_amount": numeric value or null,
  "subtotal": numeric value or null,
  "tax_amount": numeric value or null,
  "currency": "USD" or other currency code,
  "payment_terms": "payment terms or null",
  "payment_method": "payment method or null"
}}

Return ONLY the JSON object, no explanations."""

        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            response_text = response.get('response', '{}').strip()

            # Extract JSON from response (handle cases where model adds text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                metadata = json.loads(json_match.group())
                # Clean up null/None values
                return {k: v for k, v in metadata.items() if v is not None and v != "" and v != "null"}
            return {}

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {}

    def extract_metadata(self, text: str, category: str) -> Dict[str, Any]:
        """Generic metadata extraction for any category."""
        if not self.available:
            return {}

        if category == 'invoices':
            return self.extract_invoice_metadata(text)
        # Add more categories as needed
        return {}


class HybridMetadataExtractor:
    """Hybrid extraction combining rules and LLM."""

    def __init__(self, use_llm: bool = True, llm_model: str = "llama3.2:3b"):
        self.rule_extractor = RuleBasedExtractor()
        self.llm_extractor = LLMExtractor(llm_model) if use_llm else None
        self.use_llm = use_llm and OLLAMA_AVAILABLE

    def extract(self, text: str, category: str, file_metadata: Dict[str, Any]) -> BaseDocumentMetadata:
        """
        Extract metadata using hybrid approach:
        1. Try rule-based extraction first (fast)
        2. If insufficient data, use LLM (intelligent but slower)
        3. Merge and validate results
        """
        logger.info(f"Extracting metadata for category: {category}")

        # Start with rule-based extraction
        if category == 'invoices':
            rule_metadata = self.rule_extractor.extract_invoice_metadata(text)
        elif category == 'contracts':
            rule_metadata = self.rule_extractor.extract_contract_metadata(text)
        elif category == 'reports':
            rule_metadata = self.rule_extractor.extract_report_metadata(text)
        else:
            rule_metadata = {}

        extraction_method = "rule_based"
        confidence = self._calculate_confidence(rule_metadata, category)

        # If confidence is low and LLM is available, use LLM
        if confidence < 0.6 and self.use_llm and self.llm_extractor:
            logger.info("Low confidence in rule-based extraction, trying LLM...")
            llm_metadata = self.llm_extractor.extract_metadata(text, category)

            # Merge: prefer LLM results for missing fields, keep rule-based for existing
            merged_metadata = {**llm_metadata, **rule_metadata}
            extraction_method = "hybrid"
            confidence = self._calculate_confidence(merged_metadata, category)
        else:
            merged_metadata = rule_metadata

        # Add file metadata and extraction metadata
        merged_metadata.update(file_metadata)
        merged_metadata['extraction_method'] = extraction_method
        merged_metadata['extraction_confidence'] = confidence
        merged_metadata['extracted_at'] = datetime.now()

        # Create appropriate metadata instance
        metadata_class = get_metadata_class(category)
        try:
            return metadata_class(**merged_metadata)
        except Exception as e:
            logger.error(f"Failed to create metadata instance: {e}")
            # Fallback to base metadata
            return BaseDocumentMetadata(**file_metadata)

    def _calculate_confidence(self, metadata: Dict[str, Any], category: str) -> float:
        """Calculate confidence score based on extracted fields."""
        if category == 'invoices':
            required_fields = ['invoice_number', 'total_amount']
            important_fields = ['invoice_date', 'vendor_name', 'subtotal']
        elif category == 'contracts':
            required_fields = ['contract_number']
            important_fields = ['party_a', 'party_b', 'start_date']
        elif category == 'reports':
            required_fields = ['report_type']
            important_fields = ['fiscal_year', 'department']
        else:
            return 0.5

        required_score = sum(1 for f in required_fields if metadata.get(f)) / len(required_fields)
        important_score = sum(1 for f in important_fields if metadata.get(f)) / len(important_fields)

        return (required_score * 0.7) + (important_score * 0.3)


# Convenience function
def extract_metadata(text: str, category: str, file_metadata: Dict[str, Any],
                     use_llm: bool = True) -> BaseDocumentMetadata:
    """Extract metadata from document text."""
    extractor = HybridMetadataExtractor(use_llm=use_llm)
    return extractor.extract(text, category, file_metadata)
