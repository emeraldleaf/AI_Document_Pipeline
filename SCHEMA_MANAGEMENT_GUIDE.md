# Schema Management Guide

Complete guide for managing document type schemas in the AI Document Pipeline.

## Overview

Document type schemas define the metadata fields that are extracted from different types of documents. The system uses YAML configuration files to define these schemas, making it easy to add, modify, or remove document types without code changes.

## Current Schema Structure

Schemas are defined in `config/metadata_schemas.yaml` with the following structure:

```yaml
document_type_name:
  description: "Human-readable description"
  required_fields:
    - field_name_1
    - field_name_2

  fields:
    field_name:
      type: string|number|date|boolean
      description: "Field description"
      examples: ["example1", "example2"]
      required: true|false
```

## Adding New Document Types

### Step 1: Define the Schema

Edit `config/metadata_schemas.yaml` and add your new document type:

```yaml
purchase_orders:
  description: "Purchase orders for goods and services procurement"
  required_fields:
    - po_number
    - vendor_name
    - total_amount

  fields:
    po_number:
      type: string
      description: "Purchase order number or reference"
      examples: ["PO-2024-001", "ORD-12345"]
      required: true

    vendor_name:
      type: string
      description: "Vendor or supplier company name"
      examples: ["Acme Corp", "Global Supplies Inc"]
      required: true

    vendor_contact:
      type: string
      description: "Vendor contact person name"
      examples: ["John Smith", "Sarah Johnson"]

    vendor_email:
      type: string
      description: "Vendor email address"
      examples: ["orders@acme.com"]

    total_amount:
      type: number
      description: "Total purchase order amount"
      examples: [15000.00, 2500.50]
      required: true

    currency:
      type: string
      description: "Currency code (ISO 4217)"
      examples: ["USD", "EUR", "GBP"]
      required: false

    order_date:
      type: date
      description: "Purchase order date (YYYY-MM-DD)"
      examples: ["2024-11-07"]
      required: true

    delivery_date:
      type: date
      description: "Expected delivery date (YYYY-MM-DD)"
      examples: ["2024-12-01"]

    payment_terms:
      type: string
      description: "Payment terms and conditions"
      examples: ["Net 30", "50% upfront, 50% on delivery"]

    shipping_address:
      type: string
      description: "Delivery/shipping address"
      examples: ["123 Business St, City, State 12345"]

    items:
      type: string
      description: "List of items being ordered"
      examples: ["Office supplies, Computers, Software licenses"]

    approval_status:
      type: string
      description: "Approval status of the purchase order"
      examples: ["Pending", "Approved", "Rejected"]
```

### Step 2: Add Test Documents

Create test documents in the `test_documents/` directory:

```
test_documents/
├── purchase_order_001.txt
├── purchase_order_002.txt
└── ...
```

### Step 3: Add Ground Truth for Benchmarking

Edit `benchmark_extraction.py` and add ground truth data in the `load_ground_truth()` function:

```python
def load_ground_truth():
    return {
        # ... existing ground truth ...

        "purchase_order_001.txt": {
            "category": "purchase_orders",
            "po_number": "PO-2024-001",
            "vendor_name": "TechCorp Solutions",
            "vendor_contact": "Jane Doe",
            "vendor_email": "procurement@techcorp.com",
            "total_amount": 15750.00,
            "currency": "USD",
            "order_date": "2024-11-01",
            "delivery_date": "2024-11-15",
            "payment_terms": "Net 30",
            "approval_status": "Approved"
        },

        "purchase_order_002.txt": {
            "category": "purchase_orders",
            "po_number": "ORD-56789",
            "vendor_name": "Global Supplies Inc",
            "total_amount": 3200.50,
            "currency": "EUR",
            "order_date": "2024-10-28",
            "payment_terms": "50% upfront"
        }
    }
```

### Step 4: Update Category Detection (if needed)

If your document type has unique characteristics, update the `detect_document_category()` function in `benchmark_extraction.py`:

```python
def detect_document_category(content, filename):
    content_lower = content.lower()
    filename_lower = filename.lower()

    # Purchase orders
    if any(keyword in content_lower for keyword in [
        'purchase order', 'po number', 'po-', 'ord-',
        'vendor:', 'supplier:', 'procurement'
    ]) or 'po' in filename_lower:
        return 'purchase_orders'

    # ... existing detection logic ...

    return 'reports'  # default fallback
```

### Step 5: Test the New Schema

Run benchmarking to validate your new schema:

```bash
# Test the new document type specifically
python benchmark_extraction.py --category purchase_orders

# Run full benchmark to ensure no regressions
python benchmark_extraction.py --baseline --name test_new_schema
```

## Removing Document Types

### Step 1: Remove from Schema Configuration

Edit `config/metadata_schemas.yaml` and delete the entire document type section:

```yaml
# BEFORE
purchase_orders:
  description: "Purchase orders for goods and services"
  # ... entire schema definition ...

reports:
  # ... other schemas ...

# AFTER
reports:
  # ... other schemas ...
```

### Step 2: Remove Ground Truth Data

Edit `benchmark_extraction.py` and remove entries from the `load_ground_truth()` function:

```python
def load_ground_truth():
    return {
        # Remove all entries for the document type being deleted
        # "purchase_order_001.txt": {...},  # <-- Remove this
        # "purchase_order_002.txt": {...},  # <-- Remove this

        # Keep other ground truth entries
        "invoice_001.txt": {
            # ... existing data ...
        },
        # ... rest of ground truth ...
    }
```

### Step 3: Remove Category Detection Logic

Update the `detect_document_category()` function to remove detection logic for the deleted type:

```python
def detect_document_category(content, filename):
    content_lower = content.lower()
    filename_lower = filename.lower()

    # Remove purchase order detection
    # if any(keyword in content_lower for keyword in [
    #     'purchase order', 'po number', 'po-', 'ord-',
    #     'vendor:', 'supplier:', 'procurement'
    # ]) or 'po' in filename_lower:
    #     return 'purchase_orders'

    # ... keep other detection logic ...

    return 'reports'  # default fallback
```

### Step 4: Remove Test Documents (Optional)

Delete test documents for the removed type:

```bash
rm test_documents/purchase_order_*.txt
```

### Step 5: Update Documentation

Remove references to the deleted document type from:
- `DOCLING_INTEGRATION_SUMMARY.md`
- `LLM_METADATA_EXTRACTION.md`
- Any other documentation files

### Step 6: Test Removal

Run benchmarking to ensure the system still works:

```bash
python benchmark_extraction.py --baseline --name verify_removal
```

## Modifying Existing Schemas

### Adding Fields to Existing Document Types

1. **Edit the schema** in `config/metadata_schemas.yaml`:

```yaml
invoices:
  description: "Invoices and receipts"
  required_fields:
    - invoice_number
    - total_amount
    - vendor_name
    - invoice_date
    - payment_status  # <-- New required field

  fields:
    # ... existing fields ...

    payment_status:
      type: string
      description: "Payment status of the invoice"
      examples: ["Paid", "Pending", "Overdue"]
      required: true  # <-- New field
```

2. **Update ground truth** in `benchmark_extraction.py`:

```python
def load_ground_truth():
    return {
        "invoice_001.txt": {
            # ... existing fields ...
            "payment_status": "Paid"  # <-- Add new field
        },
        # ... other invoices ...
    }
```

3. **Test the changes**:

```bash
python benchmark_extraction.py --baseline --name test_schema_modification
```

### Removing Fields from Existing Document Types

1. **Remove from schema** in `config/metadata_schemas.yaml`:

```yaml
invoices:
  required_fields:
    - invoice_number
    - total_amount
    - vendor_name
    # - payment_status  # <-- Remove from required fields

  fields:
    # ... keep other fields ...
    # payment_status:  # <-- Remove entire field definition
    #   type: string
    #   ...
```

2. **Remove from ground truth** in `benchmark_extraction.py`:

```python
def load_ground_truth():
    return {
        "invoice_001.txt": {
            "invoice_number": "INV-2024-001",
            "total_amount": 1500.00,
            "vendor_name": "Acme Corp"
            # "payment_status": "Paid"  # <-- Remove field
        },
    }
```

3. **Test the changes**:

```bash
python benchmark_extraction.py --baseline --name test_field_removal
```

## Schema Validation and Best Practices

### Field Type Guidelines

- **string**: Text fields, names, descriptions
- **number**: Amounts, quantities, percentages
- **date**: Dates in YYYY-MM-DD format
- **boolean**: True/false flags

### Required vs Optional Fields

- **Required fields**: Must be present in `required_fields` list AND have `required: true`
- **Optional fields**: Not in `required_fields` list, can have `required: false` or omit the `required` key

### Naming Conventions

- Use snake_case for field names: `invoice_number`, `vendor_name`, `total_amount`
- Use descriptive names that clearly indicate the field's purpose
- Keep names consistent across document types when possible

### Examples and Descriptions

- **Always provide examples**: Help the LLM understand expected formats
- **Write clear descriptions**: Explain what the field represents and any special formatting
- **Include edge cases**: Show variations in examples (different formats, abbreviations, etc.)

### Testing Schema Changes

Always test schema changes with benchmarking:

```bash
# Test specific document type
python benchmark_extraction.py --category invoices

# Full benchmark to check for regressions
python benchmark_extraction.py --baseline --name schema_change_test

# Compare against previous baseline
python benchmark_extraction.py --compare --baseline-file benchmarks/benchmark_results_previous_baseline_*.json
```

### Schema Version Control

- **Commit schema changes** with corresponding ground truth updates
- **Document breaking changes** in commit messages
- **Test thoroughly** before deploying to production

## Troubleshooting

### Common Issues

**"Field not found in extraction results"**
- Check if field is defined in schema
- Verify field name matches between schema and ground truth
- Ensure field has proper type and description

**"Low accuracy on new document type"**
- Review field descriptions and examples
- Check if test documents match the schema expectations
- Consider if the document type needs different field definitions

**"Schema validation errors"**
- Verify YAML syntax is correct
- Check that all required fields are defined
- Ensure field types are valid (string, number, date, boolean)

**"Category detection not working"**
- Update detection keywords in `detect_document_category()`
- Check filename patterns
- Review content analysis logic

### Getting Help

If you encounter issues:
1. Check the benchmarking output for specific error messages
2. Review the `benchmark_extraction.py` logs
3. Verify schema syntax with a YAML validator
4. Test with simple examples first, then add complexity

## Examples

### Complete Purchase Order Schema

```yaml
purchase_orders:
  description: "Purchase orders for procurement and vendor management"
  required_fields:
    - po_number
    - vendor_name
    - total_amount
    - order_date

  fields:
    po_number:
      type: string
      description: "Unique purchase order identifier"
      examples: ["PO-2024-001", "ORD-12345", "PUR-67890"]
      required: true

    vendor_name:
      type: string
      description: "Name of the vendor or supplier"
      examples: ["Microsoft Corporation", "Dell Technologies", "Office Depot"]
      required: true

    vendor_contact:
      type: string
      description: "Primary contact person at the vendor"
      examples: ["John Smith", "Sarah Johnson", "Mike Wilson"]

    vendor_email:
      type: string
      description: "Vendor contact email address"
      examples: ["orders@microsoft.com", "procurement@dell.com"]

    vendor_phone:
      type: string
      description: "Vendor contact phone number"
      examples: ["+1-800-123-4567", "(555) 123-4567"]

    total_amount:
      type: number
      description: "Total monetary value of the purchase order"
      examples: [15750.00, 3200.50, 89500.75]
      required: true

    currency:
      type: string
      description: "Currency code for the transaction"
      examples: ["USD", "EUR", "GBP", "CAD"]
      required: false

    order_date:
      type: date
      description: "Date the purchase order was issued"
      examples: ["2024-11-07", "2024-10-28"]
      required: true

    delivery_date:
      type: date
      description: "Expected delivery or fulfillment date"
      examples: ["2024-11-15", "2024-12-01"]

    payment_terms:
      type: string
      description: "Payment terms and conditions"
      examples: ["Net 30", "Net 15", "50% upfront, 50% on delivery", "COD"]

    shipping_address:
      type: string
      description: "Delivery destination address"
      examples: ["123 Business St, Suite 100, New York, NY 10001"]

    billing_address:
      type: string
      description: "Billing address for invoicing"
      examples: ["456 Finance Ave, Accounting Dept, Boston, MA 02101"]

    items:
      type: string
      description: "Description of items or services being ordered"
      examples: ["Office supplies and equipment", "Software licenses for 50 users", "IT consulting services"]

    quantity:
      type: number
      description: "Total quantity of items ordered"
      examples: [50, 100, 1]

    unit_price:
      type: number
      description: "Price per unit item"
      examples: [25.00, 150.50, 5000.00]

    tax_amount:
      type: number
      description: "Tax amount included in total"
      examples: [1250.00, 256.04]

    discount_amount:
      type: number
      description: "Any discounts applied to the order"
      examples: [500.00, 0.00]

    approval_status:
      type: string
      description: "Current approval status of the purchase order"
      examples: ["Pending", "Approved", "Rejected", "Under Review"]

    approved_by:
      type: string
      description: "Name of person who approved the order"
      examples: ["Jane Manager", "Bob Director"]

    approval_date:
      type: date
      description: "Date the order was approved"
      examples: ["2024-11-08"]

    notes:
      type: string
      description: "Additional notes or special instructions"
      examples: ["Urgent delivery required", "Budget code: IT-2024-Q4"]
```

This schema provides comprehensive coverage for purchase order metadata extraction while maintaining flexibility for different procurement scenarios.</content>
<parameter name="filePath">/Users/joshuadell/Dev/AI_Document_Pipeline/SCHEMA_MANAGEMENT_GUIDE.md