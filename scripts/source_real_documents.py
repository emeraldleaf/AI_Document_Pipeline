#!/usr/bin/env python3
"""
Real Business Documents Sourcing Guide
======================================

This script helps transition from synthetic test data to real business documents
for more realistic testing and benchmarking of the document pipeline.

The goal is to replace generated test content with actual company documents
to improve accuracy testing and ensure the system works with real-world data.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger

class RealDocumentsSourcingGuide:
    """
    Guide for sourcing and organizing real business documents for testing.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.docs_dir = self.base_dir / "documents"
        self.test_docs_dir = self.base_dir / "test_documents"
        self.real_docs_dir = self.base_dir / "real_business_documents"

    def create_sourcing_structure(self):
        """Create directory structure for real document sourcing."""

        # Create main directories
        directories = [
            self.real_docs_dir,
            self.real_docs_dir / "invoices",
            self.real_docs_dir / "receipts",
            self.real_docs_dir / "contracts",
            self.real_docs_dir / "correspondence",
            self.real_docs_dir / "technical_manuals",
            self.real_docs_dir / "purchase_orders",
            self.real_docs_dir / "ground_truth",
            self.real_docs_dir / "metadata"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")

    def generate_sourcing_checklist(self) -> str:
        """Generate a comprehensive checklist for sourcing real documents."""

        checklist = """
# Real Business Documents Sourcing Checklist
==========================================

## 📋 Document Categories to Source

### 1. Invoices (Target: 20-30 documents)
- [ ] Vendor invoices from different suppliers
- [ ] Client invoices for services rendered
- [ ] Utility bills (electricity, internet, phone)
- [ ] Professional service invoices (legal, consulting, IT)
- [ ] Subscription service invoices (software, publications)

### 2. Receipts (Target: 15-20 documents)
- [ ] Point-of-sale receipts
- [ ] Online purchase receipts
- [ ] Expense receipts (meals, travel, supplies)
- [ ] Cash register receipts
- [ ] Digital receipt emails

### 3. Contracts (Target: 10-15 documents)
- [ ] Service agreements
- [ ] Vendor contracts
- [ ] Employment contracts
- [ ] Lease agreements
- [ ] Partnership agreements
- [ ] NDA agreements

### 4. Correspondence (Target: 25-30 documents)
- [ ] Business emails (internal/external)
- [ ] Meeting notes and agendas
- [ ] Project status reports
- [ ] Client communications
- [ ] Vendor correspondence
- [ ] Internal memos

### 5. Technical Manuals (Target: 5-10 documents)
- [ ] Product manuals
- [ ] Equipment specifications
- [ ] Installation guides
- [ ] User documentation
- [ ] Technical specifications

### 6. Purchase Orders (Target: 10-15 documents)
- [ ] Internal purchase orders
- [ ] Vendor purchase orders
- [ ] Procurement requests
- [ ] Order confirmations

## 🔍 Document Quality Requirements

### Content Quality
- [ ] Varied document layouts and formats
- [ ] Different vendors/suppliers
- [ ] Various date ranges (recent + historical)
- [ ] Different currencies where applicable
- [ ] Various document complexity levels

### Technical Quality
- [ ] PDF documents (scanned + digital)
- [ ] Word documents (.docx)
- [ ] Email formats (.eml, .msg)
- [ ] Images (.jpg, .png) of documents
- [ ] Mixed quality (clear + poor scans)

## 📝 Ground Truth Creation Process

### For Each Document Category:
1. **Collect Raw Documents**
   - Gather actual business documents
   - Ensure variety in format and complexity
   - Remove sensitive information if needed

2. **Create Ground Truth JSON**
   ```json
   {
     "document_id": "invoice_001",
     "filename": "vendor_invoice_2024.pdf",
     "category": "invoices",
     "expected_metadata": {
       "invoice_number": "INV-2024-001",
       "vendor_name": "Acme Corp",
       "total_amount": 1250.00,
       // ... all expected fields
     },
     "extraction_notes": "Standard vendor invoice format",
     "quality_score": "high"
   }
   ```

3. **Validate Ground Truth**
   - Cross-check with document content
   - Ensure all required fields are covered
   - Test extraction accuracy manually

## 🛠️ Implementation Steps

### Phase 1: Initial Collection (Week 1-2)
- [ ] Identify document sources within organization
- [ ] Create anonymization process for sensitive data
- [ ] Set up document collection workflow
- [ ] Begin collecting 5-10 documents per category

### Phase 2: Ground Truth Creation (Week 3-4)
- [ ] Create ground truth JSON files
- [ ] Validate accuracy of ground truth data
- [ ] Test extraction on initial documents
- [ ] Refine ground truth based on results

### Phase 3: Expansion & Testing (Week 5-6)
- [ ] Collect remaining target documents
- [ ] Create comprehensive ground truth dataset
- [ ] Run full benchmark tests
- [ ] Compare performance vs synthetic data

### Phase 4: Continuous Improvement (Ongoing)
- [ ] Add new document types as needed
- [ ] Update ground truth for edge cases
- [ ] Monitor extraction accuracy over time
- [ ] Expand test coverage

## 🔒 Privacy & Security Considerations

### Data Protection
- [ ] Remove sensitive personal information
- [ ] Anonymize customer/vendor names if needed
- [ ] Use company-approved documents only
- [ ] Comply with data retention policies

### Access Control
- [ ] Store documents in secure location
- [ ] Limit access to authorized personnel
- [ ] Use encryption for sensitive documents
- [ ] Implement audit logging

## 📊 Success Metrics

### Collection Targets
- [ ] 80+ total documents across all categories
- [ ] 5+ documents per category minimum
- [ ] Mix of digital and scanned documents

### Quality Metrics
- [ ] Ground truth accuracy: 100%
- [ ] Document variety score: >80%
- [ ] Format diversity: PDF, Word, Email, Images

### Performance Impact
- [ ] Extraction accuracy improvement: +5-10%
- [ ] Processing time stability: ±10%
- [ ] Error rate reduction: -20%

## 🚀 Getting Started

1. **Review this checklist** with your team
2. **Identify document sources** within your organization
3. **Create anonymization guidelines** for sensitive data
4. **Set up collection process** and assign responsibilities
5. **Begin with 1-2 categories** to establish workflow
6. **Create initial ground truth** and test extraction
7. **Scale up collection** based on initial results

## 📞 Support Resources

- **Document Pipeline Team**: For technical questions
- **Legal/Compliance**: For data privacy questions
- **IT Security**: For secure storage solutions
- **Procurement**: For accessing vendor documents

---
*This checklist ensures systematic transition from synthetic to real business documents for improved testing accuracy.*
"""

        return checklist

    def create_document_template(self, category: str) -> Dict[str, Any]:
        """Create a template for document ground truth."""

        templates = {
            "invoices": {
                "document_id": "invoice_001",
                "filename": "sample_invoice.pdf",
                "category": "invoices",
                "expected_metadata": {
                    "invoice_number": "INV-2024-001",
                    "invoice_date": "2024-01-15",
                    "vendor_name": "Sample Vendor Corp",
                    "total_amount": 1250.00,
                    "currency": "USD"
                },
                "extraction_notes": "Standard business invoice",
                "quality_score": "high"
            },
            "contracts": {
                "document_id": "contract_001",
                "filename": "service_contract.pdf",
                "category": "contracts",
                "expected_metadata": {
                    "contract_number": "CON-2024-001",
                    "contract_date": "2024-01-01",
                    "party_a": "Company A",
                    "party_b": "Company B",
                    "contract_value": 50000.00
                },
                "extraction_notes": "Standard service agreement",
                "quality_score": "high"
            }
        }

        return templates.get(category, {})

    def generate_ground_truth_template(self) -> str:
        """Generate a template for creating ground truth files."""

        template = '''{
  "dataset_name": "real_business_documents",
  "version": "1.0",
  "description": "Ground truth for real business documents testing",
  "documents": [
    {
      "document_id": "DOCUMENT_ID",
      "filename": "actual_filename.pdf",
      "category": "document_category",
      "source": "anonymized_company_data",
      "expected_metadata": {
        // Fill in expected extraction results
        // Use actual values from the document
      },
      "extraction_notes": "Notes about document complexity or special features",
      "quality_score": "high|medium|low",
      "anonymization_applied": true|false,
      "created_date": "2024-11-13"
    }
  ]
}'''

        return template

    def create_sourcing_script(self):
        """Create a helper script for document organization."""

        script_content = '''#!/usr/bin/env python3
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
'''

        script_path = self.real_docs_dir / "sourcing_helper.py"
        with open(script_path, 'w') as f:
            f.write(script_content)

        # Make executable
        os.chmod(script_path, 0o755)
        logger.info(f"Created sourcing helper script: {script_path}")

def main():
    """Main function to set up real document sourcing."""

    guide = RealDocumentsSourcingGuide()

    # Create directory structure
    guide.create_sourcing_structure()

    # Generate and save checklist
    checklist = guide.generate_sourcing_checklist()
    checklist_path = guide.real_docs_dir / "SOURCING_CHECKLIST.md"
    with open(checklist_path, 'w') as f:
        f.write(checklist)

    # Generate ground truth template
    template = guide.generate_ground_truth_template()
    template_path = guide.real_docs_dir / "ground_truth_template.json"
    with open(template_path, 'w') as f:
        f.write(template)

    # Create helper script
    guide.create_sourcing_script()

    logger.info("Real business documents sourcing setup complete!")
    logger.info(f"Check {guide.real_docs_dir} for guides and templates")

if __name__ == "__main__":
    main()