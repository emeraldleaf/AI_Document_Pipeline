"""
LLM-Based Configurable Metadata Extraction
============================================

Flexible metadata extraction using:
- Configuration-driven schema definitions (YAML)
- LLM-based intelligent extraction (Ollama)
- Dynamic schema loading for any document type
- Easy extensibility without code changes
"""

import json
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not available, LLM extraction will be disabled")


class ConfigurableMetadataExtractor:
    """
    LLM-based metadata extractor with configurable schemas.

    Loads schema definitions from YAML and uses LLM to extract
    structured metadata according to those schemas.
    """

    def __init__(
        self,
        schema_path: str = None,
        model: str = "llama3.2:3b",
        max_text_length: int = 4000
    ):
        """
        Initialize the extractor.

        Args:
            schema_path: Path to YAML schema configuration file
            model: Ollama model to use for extraction
            max_text_length: Maximum text length to send to LLM
        """
        self.model = model
        self.max_text_length = max_text_length
        self.available = OLLAMA_AVAILABLE

        # Load schema configuration
        if schema_path is None:
            # Default to config/metadata_schemas.yaml
            base_path = Path(__file__).parent.parent
            schema_path = base_path / "config" / "metadata_schemas.yaml"

        self.schema_path = Path(schema_path)
        self.schemas = self._load_schemas()

        logger.info(f"Loaded {len(self.schemas)} metadata schemas from {self.schema_path}")
        logger.info(f"Available categories: {list(self.schemas.keys())}")

    def _load_schemas(self) -> Dict[str, Any]:
        """Load schema definitions from YAML file."""
        if not self.schema_path.exists():
            logger.warning(f"Schema file not found: {self.schema_path}")
            return {}

        try:
            with open(self.schema_path, 'r') as f:
                schemas = yaml.safe_load(f)
            return schemas or {}
        except Exception as e:
            logger.error(f"Failed to load schemas: {e}")
            return {}

    def get_schema(self, category: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific document category."""
        return self.schemas.get(category.lower())

    def _build_extraction_prompt(self, text: str, category: str) -> str:
        """
        Build the LLM prompt for metadata extraction.

        Args:
            text: Document text to extract from
            category: Document category

        Returns:
            Formatted prompt for the LLM
        """
        schema = self.get_schema(category)

        if not schema:
            logger.warning(f"No schema found for category: {category}")
            return self._build_generic_prompt(text)

        # Truncate text if needed
        text_sample = text[:self.max_text_length]
        if len(text) > self.max_text_length:
            logger.debug(f"Text truncated from {len(text)} to {self.max_text_length} characters")

        # Build JSON schema description for the LLM
        fields_description = self._format_fields_for_prompt(schema.get('fields', {}))

        # Simpler, more direct prompt that works better with smaller models
        prompt = f"""Extract metadata from this invoice/receipt and return as JSON.

Document text:
---
{text_sample}
---

Extract ALL these fields (use null if not found):
{fields_description}

Return ONLY the JSON object with NO other text. Use YYYY-MM-DD for dates, numbers (not strings) for amounts.

JSON:"""

        return prompt

    def _format_fields_for_prompt(self, fields: Dict[str, Any]) -> str:
        """Format field definitions for the prompt."""
        lines = []

        for field_name, field_config in fields.items():
            field_type = field_config.get('type', 'string')
            description = field_config.get('description', '')
            examples = field_config.get('examples', [])

            line = f"- {field_name} ({field_type}): {description}"

            if examples:
                examples_str = ', '.join(f'"{ex}"' if isinstance(ex, str) else str(ex) for ex in examples[:3])
                line += f" [Examples: {examples_str}]"

            lines.append(line)

        return '\n'.join(lines)

    def _build_generic_prompt(self, text: str) -> str:
        """Build a generic extraction prompt when no schema is available."""
        text_sample = text[:self.max_text_length]

        return f"""Extract key metadata from this document as JSON.

Document text:
{text_sample}

Extract relevant information such as:
- Dates (in YYYY-MM-DD format)
- Names of people or organizations
- Amounts or financial values
- Reference numbers or IDs
- Any other important structured information

Return ONLY valid JSON (no other text):"""

    def extract(
        self,
        text: str,
        category: str,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract metadata from document text.

        Args:
            text: Full document text
            category: Document category (e.g., 'invoices', 'contracts')
            file_metadata: Additional file-level metadata to merge

        Returns:
            Dictionary containing extracted metadata
        """
        if not self.available:
            logger.error("Ollama not available - cannot extract metadata")
            return file_metadata or {}

        if not text or not text.strip():
            logger.warning("Empty text provided for extraction")
            return file_metadata or {}

        logger.info(f"Extracting metadata for category: {category}")

        # Build prompt
        prompt = self._build_extraction_prompt(text, category)

        # Call LLM
        try:
            logger.debug(f"Calling Ollama model: {self.model}")

            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,  # Low temperature for factual extraction
                    "top_p": 0.9,
                    "num_predict": 2000,  # Allow longer responses
                }
            )

            response_text = response.get('response', '{}').strip()
            logger.debug(f"LLM response length: {len(response_text)} characters")
            logger.debug(f"LLM response (first 500 chars): {response_text[:500]}")

            # Extract JSON from response
            metadata = self._extract_json_from_response(response_text)

            # Validate and clean metadata
            metadata = self._validate_metadata(metadata, category)

            # Add extraction metadata
            metadata['extraction_method'] = 'llm'
            metadata['extraction_model'] = self.model
            metadata['extraction_confidence'] = self._calculate_confidence(metadata, category)
            metadata['extracted_at'] = datetime.now().isoformat()

            # Merge with file metadata if provided
            if file_metadata:
                metadata = {**file_metadata, **metadata}

            logger.info(f"✓ Extraction complete (confidence: {metadata['extraction_confidence']:.2f})")

            return metadata

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            logger.exception(e)
            return file_metadata or {}

    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract JSON object from LLM response.

        Handles cases where the LLM adds markdown formatting or extra text.
        """
        # Try to find JSON object in response
        # Look for content between curly braces
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                logger.debug(f"Problematic JSON: {json_match.group()[:200]}")

        # Try parsing the entire response as JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Could not find valid JSON in response")
            logger.debug(f"Response text: {response_text[:500]}")
            return {}

    def _validate_metadata(self, metadata: Dict[str, Any], category: str) -> Dict[str, Any]:
        """
        Validate and clean extracted metadata according to schema.

        Args:
            metadata: Extracted metadata
            category: Document category

        Returns:
            Cleaned and validated metadata
        """
        schema = self.get_schema(category)
        if not schema:
            return self._clean_null_values(metadata)

        fields_config = schema.get('fields', {})
        cleaned = {}

        for field_name, value in metadata.items():
            # Skip null/empty values
            if value is None or value == "" or value == "null":
                continue

            field_config = fields_config.get(field_name, {})
            field_type = field_config.get('type', 'string')

            # Type validation and conversion
            try:
                if field_type == 'number':
                    cleaned[field_name] = float(value) if value else None
                elif field_type == 'integer':
                    cleaned[field_name] = int(value) if value else None
                elif field_type == 'boolean':
                    if isinstance(value, bool):
                        cleaned[field_name] = value
                    elif isinstance(value, str):
                        cleaned[field_name] = value.lower() in ('true', 'yes', '1')
                elif field_type in ('date', 'datetime'):
                    # Keep as string in ISO format
                    cleaned[field_name] = value
                elif field_type == 'array':
                    if isinstance(value, list):
                        cleaned[field_name] = value
                    elif isinstance(value, str):
                        # Try to parse as JSON array
                        try:
                            cleaned[field_name] = json.loads(value)
                        except:
                            # Split by comma as fallback
                            cleaned[field_name] = [v.strip() for v in value.split(',')]
                else:
                    # String or unknown type
                    cleaned[field_name] = str(value)

            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to validate field {field_name}: {e}")
                # Keep original value if conversion fails
                cleaned[field_name] = value

        return cleaned

    def _clean_null_values(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Remove null/empty values from metadata."""
        return {
            k: v for k, v in metadata.items()
            if v is not None and v != "" and v != "null"
        }

    def _calculate_confidence(self, metadata: Dict[str, Any], category: str) -> float:
        """
        Calculate confidence score for extraction.

        Based on:
        - Presence of required fields
        - Number of fields extracted
        - Schema completeness
        """
        schema = self.get_schema(category)

        if not schema:
            # No schema - base confidence on number of fields
            return min(len(metadata) / 5, 1.0) * 0.5  # Max 0.5 without schema

        required_fields = schema.get('required_fields', [])
        all_fields = list(schema.get('fields', {}).keys())

        if not required_fields and not all_fields:
            return 0.5

        # Calculate required field score
        if required_fields:
            required_score = sum(
                1 for field in required_fields
                if field in metadata and metadata[field]
            ) / len(required_fields)
        else:
            required_score = 1.0

        # Calculate optional field score
        if all_fields:
            optional_score = len([
                f for f in all_fields
                if f in metadata and metadata[f]
            ]) / len(all_fields)
        else:
            optional_score = 0.5

        # Weighted combination (required fields are more important)
        confidence = (required_score * 0.7) + (optional_score * 0.3)

        return round(confidence, 2)

    def extract_batch(
        self,
        documents: List[Dict[str, Any]],
        category_field: str = 'category',
        text_field: str = 'text'
    ) -> List[Dict[str, Any]]:
        """
        Extract metadata from multiple documents.

        Args:
            documents: List of document dicts with 'text' and 'category' fields
            category_field: Field name for category
            text_field: Field name for text content

        Returns:
            List of extracted metadata dicts
        """
        results = []

        for i, doc in enumerate(documents):
            logger.info(f"Processing document {i+1}/{len(documents)}")

            text = doc.get(text_field, '')
            category = doc.get(category_field, 'unknown')

            metadata = self.extract(text, category, file_metadata=doc)
            results.append(metadata)

        return results


# Convenience function
def extract_metadata(
    text: str,
    category: str,
    file_metadata: Optional[Dict[str, Any]] = None,
    model: str = "llama3.2:3b"
) -> Dict[str, Any]:
    """
    Extract metadata from document text using LLM.

    Args:
        text: Document text
        category: Document category
        file_metadata: Additional file metadata to merge
        model: Ollama model to use

    Returns:
        Extracted metadata dictionary
    """
    extractor = ConfigurableMetadataExtractor(model=model)
    return extractor.extract(text, category, file_metadata)
