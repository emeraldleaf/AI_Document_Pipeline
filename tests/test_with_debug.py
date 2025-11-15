#!/usr/bin/env python3
"""Test with debug logging enabled."""

import sys
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Enable DEBUG logging
logger.remove()
logger.add(sys.stderr, level="DEBUG")

from llm_metadata_extractor import ConfigurableMetadataExtractor

# Read test receipt
receipt_path = Path(__file__).parent / "test_documents" / "receipt_001.txt"
content = receipt_path.read_text()

print("\n" + "=" * 80)
print("TESTING LLM EXTRACTION WITH DEBUG OUTPUT")
print("=" * 80 + "\n")

# Extract
extractor = ConfigurableMetadataExtractor(model="llama3.2:3b")
metadata = extractor.extract(
    text=content,
    category="invoices",
    file_metadata={"file_name": "receipt_001.txt"}
)

import json
print("\n" + "=" * 80)
print("RESULT:")
print("=" * 80)
print(json.dumps(metadata, indent=2, default=str))
