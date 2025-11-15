
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
