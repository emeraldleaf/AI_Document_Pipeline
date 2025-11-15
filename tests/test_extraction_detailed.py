#!/usr/bin/env python3
"""Test LLM extraction with verbose output to see what's happening."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm_metadata_extractor import ConfigurableMetadataExtractor

# Read the test receipt
receipt_path = Path(__file__).parent / "test_documents" / "receipt_001.txt"
content = receipt_path.read_text()

print("=" * 80)
print("DOCUMENT CONTENT (first 500 chars):")
print("=" * 80)
print(content[:500])
print("\n")

print("=" * 80)
print("EXTRACTING METADATA...")
print("=" * 80)

# Extract
extractor = ConfigurableMetadataExtractor(model="llama3.2:3b")
metadata = extractor.extract(
    text=content,
    category="invoices",
    file_metadata={"file_name": "receipt_001.txt"}
)

print("\n" + "=" * 80)
print("FULL EXTRACTED METADATA:")
print("=" * 80)
print(json.dumps(metadata, indent=2, default=str))

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)
print(f"Fields extracted: {len([k for k, v in metadata.items() if v and k not in ['file_name', 'extraction_method', 'extraction_model', 'extraction_confidence', 'extracted_at']])}")
print(f"Confidence score: {metadata.get('extraction_confidence')}")

# Check what should have been extracted
expected_fields = {
    'invoice_number': 'REC-2024-10-31-001',
    'invoice_date': '2024-10-31',
    'vendor_name': 'Office Supplies Plus',
    'vendor_address': '555 Commerce Street, Seattle, WA 98101',
    'vendor_phone': '(206) 555-0200',
    'customer_name': 'Sarah Johnson',
    'subtotal': 204.33,
    'tax_amount': 20.64,
    'total_amount': 224.97,
    'payment_method': 'Corporate Credit Card',
    'item_count': 8
}

print("\n" + "=" * 80)
print("FIELD COMPARISON:")
print("=" * 80)
for field, expected in expected_fields.items():
    actual = metadata.get(field)
    status = "✓" if actual else "✗"
    print(f"{status} {field:20s} Expected: {str(expected):30s} Got: {actual}")
