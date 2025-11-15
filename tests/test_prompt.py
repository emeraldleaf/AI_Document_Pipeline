#!/usr/bin/env python3
"""View the actual prompt being sent to the LLM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from llm_metadata_extractor import ConfigurableMetadataExtractor

# Read test receipt
receipt_path = Path(__file__).parent / "test_documents" / "receipt_001.txt"
content = receipt_path.read_text()

# Create extractor
extractor = ConfigurableMetadataExtractor(model="llama3.2:3b")

# Build prompt
prompt = extractor._build_extraction_prompt(content, "invoices")

print("=" * 80)
print("FULL PROMPT SENT TO LLM:")
print("=" * 80)
print(prompt)
print("=" * 80)
print(f"Prompt length: {len(prompt)} characters")
