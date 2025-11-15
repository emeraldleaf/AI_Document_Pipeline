#!/usr/bin/env python3
"""
Document Sourcing Helper Script
===============================

Helps organize and validate real business documents for testing.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List

def validate_document_structure(docs_dir: str) -> Dict[str, int]:
    """Validate that documents are properly organized by category."""

    docs_path = Path(docs_dir)
    categories = ['invoices', 'receipts', 'contracts', 'correspondence',
                 'technical_manuals', 'purchase_orders']

    stats = {}
    for category in categories:
        category_path = docs_path / category
        if category_path.exists():
            doc_count = len(list(category_path.glob('*')))
            stats[category] = doc_count
        else:
            stats[category] = 0

    return stats

def create_ground_truth_template(category: str, filename: str) -> Dict:
    """Create a ground truth template for a document."""

    templates = {
        'invoices': {
            'invoice_number': '',
            'invoice_date': '',
            'vendor_name': '',
            'total_amount': 0.0,
            'currency': 'USD'
        },
        'contracts': {
            'contract_number': '',
            'contract_date': '',
            'party_a': '',
            'party_b': '',
            'contract_value': 0.0
        }
    }

    return {
        'document_id': f"{category}_{Path(filename).stem}",
        'filename': filename,
        'category': category,
        'expected_metadata': templates.get(category, {}),
        'extraction_notes': '',
        'quality_score': 'high'
    }

if __name__ == "__main__":
    # Example usage
    docs_dir = "real_business_documents"
    stats = validate_document_structure(docs_dir)

    print("Document Collection Status:")
    for category, count in stats.items():
        status = "✅" if count >= 5 else "⚠️" if count > 0 else "❌"
        print(f"{status} {category}: {count} documents")
