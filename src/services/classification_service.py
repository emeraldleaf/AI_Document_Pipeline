"""
==============================================================================
CLASSIFICATION SERVICE - AI-Powered Document Classification
==============================================================================

PURPOSE:
    Classify documents into categories using Large Language Models (LLMs).
    This is the "brain" that decides what type of document we're looking at.

WHAT IS CLASSIFICATION?
    Taking a document's content and assigning it to a category:
    - Invoice → "invoices"
    - Contract → "contracts"
    - Receipt → "receipts"
    - Report → "reports"

HOW IT WORKS:
    1. Take extracted text from a document
    2. Build a prompt for the AI (includes text + metadata + categories)
    3. Send prompt to Ollama (local AI service)
    4. Parse AI's response (JSON with category + confidence + reasoning)
    5. Validate and return classification result

WHAT IS OLLAMA?
    - A local AI service that runs language models (like ChatGPT but local)
    - Runs on your machine (no cloud, no API keys needed)
    - Models: llama3.2, mistral, etc.
    - API: REST HTTP endpoints at localhost:11434

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                  Document Classification Flow                │
    │                                                             │
    │  1. ExtractedContent (text + metadata)                      │
    │           ↓                                                 │
    │  2. Build Prompt (include categories, examples)             │
    │           ↓                                                 │
    │  3. Send to Ollama API                                      │
    │           ↓                                                 │
    │  4. Ollama runs LLM (llama3.2)                             │
    │           ↓                                                 │
    │  5. Parse JSON response                                     │
    │           ↓                                                 │
    │  6. Validate category + confidence                          │
    │           ↓                                                 │
    │  7. Return ClassificationResult                             │
    └─────────────────────────────────────────────────────────────┘

KEY CONCEPTS:
    1. **LLM (Large Language Model)**: AI that understands and generates text
    2. **Prompt Engineering**: Crafting input text to get good AI responses
    3. **Temperature**: Controls randomness (0.0=deterministic, 1.0=creative)
    4. **Tokens**: Words/pieces of words (max_tokens limits response length)
    5. **Confidence Score**: How sure the AI is (0.0-1.0)
    6. **Protocol-Based Design**: Implements ClassificationService protocol

PROTOCOL-BASED ARCHITECTURE:
    This service implements the ClassificationService protocol from domain layer.

    Benefits:
    - Can swap out Ollama for OpenAI, Claude, etc. without changing callers
    - Dependency Injection: Pass in any service that implements the protocol
    - Testable: Easy to create mock services for testing
    - SOLID principles: Depend on abstractions, not implementations

EXAMPLE USAGE:
    ```python
    from src.services.classification_service import OllamaClassificationService
    from src.domain import ExtractedContent

    # Create service
    service = OllamaClassificationService(
        host="http://localhost:11434",
        model="llama3.2",
        temperature=0.1  # Low temperature for consistent results
    )

    # Check if Ollama is running
    if await service.is_available():
        # Classify a document
        content = ExtractedContent(text="...", metadata=...)
        categories = ["invoices", "contracts", "reports", "other"]

        result = await service.classify_document(content, categories)

        if result.is_success:
            classification = result.value
            print(f"Category: {classification.category}")
            print(f"Confidence: {classification.confidence:.2%}")
            print(f"Reasoning: {classification.reasoning}")
        else:
            print(f"Error: {result.error}")
    ```

RELATED FILES:
    - src/domain/protocols.py - ClassificationService protocol definition
    - src/domain/models.py - ClassificationResult model
    - src/ollama_service.py - Legacy Ollama service (being replaced)
    - src/classifier.py - Main classifier that uses this service

AUTHOR: AI Document Pipeline Team
LAST UPDATED: October 2025
"""

import json
from typing import List, Dict, Any, Optional
import requests
import logging

from ..domain import (
    ClassificationService,
    ExtractedContent,
    ClassificationResult,
    Result,
    ClassificationError,
    ConfigurationProvider,
)


logger = logging.getLogger(__name__)


# ==============================================================================
# OLLAMA CLASSIFICATION SERVICE
# ==============================================================================

class OllamaClassificationService:
    """
    Document classification service using Ollama LLM.

    WHAT IT DOES:
        Sends document text to a local Ollama AI service and gets back
        a category, confidence score, and reasoning.

    HOW IT WORKS:
        1. Builds a carefully crafted prompt (prompt engineering)
        2. Sends HTTP POST request to Ollama API
        3. Parses JSON response from AI
        4. Validates and returns classification result

    KEY FEATURES:
        - **Protocol Implementation**: Implements ClassificationService protocol
        - **Error Handling**: Returns Result type (no exceptions)
        - **Prompt Engineering**: Includes examples and constraints
        - **Response Validation**: Ensures category is valid
        - **Configurable**: Temperature, timeout, max tokens

    TUNING PARAMETERS:
        temperature:
            - 0.0-0.2: Very consistent, deterministic (RECOMMENDED for classification)
            - 0.3-0.7: Balanced
            - 0.8-1.0: Creative, varied (not good for classification)
            Why low? We want the same document to get the same category!

        max_tokens:
            - 500-1000: Good for classification responses (RECOMMENDED)
            - 1000+: For longer explanations
            Why limit? Classification responses are short, no need for 4000 tokens

        timeout:
            - 60-120s: Good for most documents (RECOMMENDED)
            - 30s: Fast but may timeout on slow models
            - 180s+: Very patient, for slow systems

    EXAMPLE:
        ```python
        service = OllamaClassificationService(
            host="http://localhost:11434",
            model="llama3.2",
            temperature=0.1,  # Very consistent
            timeout=120,      # 2 minutes max
            max_tokens=1000   # Enough for response
        )
        ```

    IMPLEMENTATION NOTES:
        - Implements ClassificationService protocol (can be swapped)
        - Returns Result type (explicit success/failure)
        - Async methods (uses await for I/O)
        - Immutable configuration (set in __init__)
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: int = 120,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ):
        """
        Initialize Ollama classification service.

        Args:
            host: Ollama API host URL (default: http://localhost:11434)
            model: Model name to use (default: llama3.2)
            timeout: Request timeout in seconds (default: 120)
            temperature: Sampling temperature 0.0-1.0 (default: 0.1 for consistency)
            max_tokens: Maximum tokens to generate (default: 1000)

        What happens during initialization:
        1. Store configuration parameters
        2. Build API endpoint URLs
        3. Set up service (no connections yet)

        Why store configuration?
        - Immutable: Can't change after creation (predictable behavior)
        - Each service instance has its own config
        - Easy to create multiple services with different settings

        Why http://localhost:11434?
        - Default Ollama installation port
        - Local = private, fast, no API costs
        - Can change to remote Ollama if needed

        Why temperature=0.1?
        - Classification needs consistency
        - Same document should get same category
        - Low temperature = less randomness
        - High temperature = more creative but inconsistent
        """
        # Step 1: Store core configuration
        self.host = host
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Step 2: Build API endpoint URLs
        # Ollama has two endpoints:
        # - /api/generate: Single prompt-response (we use this)
        # - /api/chat: Multi-turn conversation
        self.api_url = f"{self.host}/api/generate"
        self.api_chat_url = f"{self.host}/api/chat"

    # ==========================================================================
    # SERVICE AVAILABILITY
    # ==========================================================================

    async def is_available(self) -> bool:
        """
        Check if the Ollama service is available and responding.

        This is a health check that:
        1. Sends HTTP GET to /api/tags endpoint
        2. Checks if response is 200 OK
        3. Returns True if available, False otherwise

        Returns:
            True if Ollama is available, False otherwise

        Why check availability?
        - Ollama might not be running (user forgot to start it)
        - Network issues (firewall, wrong host)
        - Better to check first than fail later
        - Provides clear error messages

        When to call this:
        - Before batch processing (check once at start)
        - After connection errors (is it still running?)
        - In health checks / monitoring

        Example:
            >>> service = OllamaClassificationService()
            >>> if await service.is_available():
            ...     print("Ready to classify!")
            ... else:
            ...     print("Please start Ollama: ollama serve")
        """
        try:
            # Send HTTP GET to tags endpoint
            # This is a lightweight endpoint that lists available models
            # Perfect for health checks
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            available = response.status_code == 200

            if available:
                logger.info("Ollama service is available")
            else:
                logger.warning(f"Ollama service returned status {response.status_code}")

            return available

        except Exception as e:
            # Connection failed (service not running, wrong host, etc.)
            logger.error(f"Ollama service not available: {e}")
            return False

    # ==========================================================================
    # CLASSIFICATION METHODS
    # ==========================================================================

    async def classify_document(
        self,
        content: ExtractedContent,
        categories: List[str]
    ) -> Result[ClassificationResult]:
        """
        Classify document content into predefined categories using AI.

        This is the main classification method. It:
        1. Checks if Ollama is available
        2. Builds a classification prompt
        3. Sends prompt to Ollama API
        4. Parses AI's response
        5. Validates and returns result

        Args:
            content: Extracted document content (text + metadata)
            categories: List of possible categories (e.g., ["invoices", "contracts"])

        Returns:
            Result containing:
                - Success: ClassificationResult (category, confidence, reasoning)
                - Failure: Error message string

        Flow:
            ExtractedContent → Build Prompt → Send to AI → Parse Response → Validate → Return

        Example:
            >>> content = ExtractedContent(
            ...     text="Invoice #12345 from Acme Corp...",
            ...     metadata=DocumentMetadata(...)
            ... )
            >>> categories = ["invoices", "contracts", "reports", "other"]
            >>>
            >>> result = await service.classify_document(content, categories)
            >>>
            >>> if result.is_success:
            ...     classification = result.value
            ...     print(f"Category: {classification.category}")
            ...     print(f"Confidence: {classification.confidence:.1%}")
            ... else:
            ...     print(f"Error: {result.error}")

        Why async?
        - Calling Ollama API takes time (1-5 seconds)
        - Async allows other tasks to run while waiting
        - Essential for batch processing (process many docs concurrently)

        Why Result type?
        - No exceptions (explicit error handling)
        - Caller can check is_success before accessing value
        - Errors are values, not control flow
        - Easier to chain operations
        """
        try:
            # Step 1: Check if Ollama service is available
            #
            # Why check first?
            # - Avoid long timeouts if service is down
            # - Provide clear error message
            # - Fail fast rather than fail slow
            if not await self.is_available():
                return Result.failure("Ollama service is not available")

            # Step 2: Build classification prompt
            #
            # This is where "prompt engineering" happens.
            # The quality of the prompt directly affects classification accuracy.
            # See _build_classification_prompt for details.
            prompt = self._build_classification_prompt(content, categories)

            # Step 3: Generate classification using Ollama
            #
            # Send HTTP request to Ollama API with the prompt.
            # This is the I/O operation that takes 1-5 seconds.
            response = await self._generate_response(prompt)
            if not response.is_success:
                return Result.failure(f"Failed to generate classification: {response.error}")

            # Step 4: Parse response into classification result
            #
            # AI returns text like: {"category": "invoices", "confidence": 0.95, ...}
            # We parse this JSON and create a ClassificationResult object.
            return self._parse_classification_response(response.value, categories)

        except Exception as e:
            # Unexpected error (shouldn't happen but handle gracefully)
            error_msg = f"Classification failed: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

    # ==========================================================================
    # PROMPT ENGINEERING
    # ==========================================================================

    def _build_classification_prompt(
        self,
        content: ExtractedContent,
        categories: List[str]
    ) -> str:
        """
        Build the classification prompt for the LLM.

        This is "prompt engineering" - crafting the input to get good AI responses.

        The prompt includes:
        1. Role definition ("You are a document classifier")
        2. Task description (classify into categories)
        3. File metadata (name, type, size)
        4. Available categories (the options)
        5. Document content (truncated if too long)
        6. Response format (JSON with specific fields)
        7. Example response (shows AI what we want)

        Args:
            content: ExtractedContent with text and metadata
            categories: List of category options

        Returns:
            Formatted prompt string ready for AI

        Why truncate to 3000 characters?
        - LLMs have token limits (e.g., 4096 tokens)
        - Usually the beginning of a document is most informative
        - Keeps prompts fast and under limits
        - 3000 chars ≈ 750-1000 tokens (leaves room for prompt + response)

        Why include metadata?
        - File name often hints at category (invoice_2024.pdf)
        - File type matters (PDF vs DOCX)
        - Gives AI more context

        Why include example response?
        - Shows AI the exact format we want
        - Reduces parsing errors
        - Called "few-shot prompting"

        Example prompt:
            ```
            You are a document classifier. Your task is to classify...

            File name: invoice_2024.pdf
            File type: pdf
            Available categories: invoices, contracts, reports, other

            Document content:
            Invoice #12345
            Date: 2024-10-01
            Amount: $1,234.56
            ...

            Please respond with a JSON object containing:
            - "category": the most appropriate category
            - "confidence": 0.0-1.0
            - "reasoning": brief explanation

            Example: {"category": "invoice", "confidence": 0.95, ...}
            ```
        """
        # Step 1: Truncate content if too long
        #
        # Why 3000 chars?
        # - LLMs have context windows (e.g., 4K tokens)
        # - Need room for prompt + response
        # - 3000 chars ≈ 750-1000 tokens
        # - Document start is usually most informative
        text = content.text[:3000] if len(content.text) > 3000 else content.text

        # Step 2: Build metadata section (if available)
        #
        # File metadata provides useful classification hints:
        # - File name: "invoice_2024.pdf" → probably an invoice
        # - File type: .xlsx → might be a report
        # - File size: Very small → might be a simple receipt
        metadata_info = ""
        if content.metadata:
            metadata_info = f"""
File name: {content.metadata.file_name}
File type: {content.metadata.file_type}
File size: {content.metadata.file_size} bytes
"""

        # Step 3: Build the full prompt
        #
        # Prompt structure (order matters!):
        # 1. Role ("You are a document classifier")
        # 2. Task ("classify into categories")
        # 3. Context (metadata + categories)
        # 4. Input (document content)
        # 5. Output format (JSON structure)
        # 6. Example (shows desired format)
        prompt = f"""You are a document classifier. Your task is to classify the following document into one of the provided categories.

{metadata_info}
Available categories: {', '.join(categories)}

Document content:
{text}

Please respond with a JSON object containing:
- "category": the most appropriate category from the list
- "confidence": a confidence score between 0.0 and 1.0
- "reasoning": brief explanation for your choice

Example response:
{{"category": "invoice", "confidence": 0.95, "reasoning": "Contains billing information, amounts, and vendor details typical of an invoice"}}

Response:"""

        return prompt

    # ==========================================================================
    # OLLAMA API COMMUNICATION
    # ==========================================================================

    async def _generate_response(self, prompt: str) -> Result[str]:
        """
        Generate response from Ollama API.

        This sends an HTTP POST request to Ollama's /api/generate endpoint.

        Args:
            prompt: The prompt to send to the AI

        Returns:
            Result containing:
                - Success: Generated text from AI
                - Failure: Error message

        API Request Format:
            ```json
            {
                "model": "llama3.2",
                "prompt": "Classify this document...",
                "stream": false,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1000
                }
            }
            ```

        API Response Format:
            ```json
            {
                "model": "llama3.2",
                "response": "{"category": "invoices", ...}",
                "done": true
            }
            ```

        Why stream=false?
        - Streaming is for real-time output (like ChatGPT typing)
        - We want the complete response at once
        - Easier to parse complete JSON

        Why Result type?
        - Network requests can fail (timeout, connection error)
        - Ollama might return errors
        - Explicit error handling (no exceptions)

        Error handling:
        - Timeout: Service too slow or unresponsive
        - Connection error: Service not running
        - HTTP error: Service error (500, 404, etc.)
        """
        try:
            # Step 1: Build API request payload
            #
            # Key parameters:
            # - model: Which AI model to use (llama3.2, mistral, etc.)
            # - prompt: The text to send to AI
            # - stream: false = wait for complete response
            # - options.temperature: Randomness (0.1 = very consistent)
            # - options.num_predict: Max tokens in response
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # Wait for complete response
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            }

            # Step 2: Send HTTP POST request to Ollama
            #
            # This is the I/O operation that takes time (1-5 seconds).
            # The request includes:
            # - URL: http://localhost:11434/api/generate
            # - Body: JSON payload with model + prompt
            # - Timeout: Max wait time (default 120s)
            logger.debug(f"Sending classification request to Ollama: {self.model}")
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout
            )

            # Step 3: Check for HTTP errors
            # raise_for_status() throws exception if status is 4xx or 5xx
            response.raise_for_status()

            # Step 4: Parse JSON response
            result = response.json()
            generated_text = result.get("response", "")

            # Step 5: Validate response is not empty
            if not generated_text:
                return Result.failure("Empty response from Ollama")

            logger.debug(f"Received response from Ollama: {len(generated_text)} characters")
            return Result.success(generated_text)

        except requests.Timeout:
            # Request took longer than timeout
            # Common causes:
            # - Model is slow (try faster model)
            # - System is overloaded
            # - Increase timeout if needed
            return Result.failure("Request to Ollama timed out")

        except requests.RequestException as e:
            # Connection or HTTP error
            # Common causes:
            # - Ollama not running
            # - Wrong host/port
            # - Network issues
            return Result.failure(f"Request failed: {e}")

        except Exception as e:
            # Unexpected error (parsing, etc.)
            return Result.failure(f"Unexpected error: {e}")

    # ==========================================================================
    # RESPONSE PARSING
    # ==========================================================================

    def _parse_classification_response(
        self,
        response_text: str,
        categories: List[str]
    ) -> Result[ClassificationResult]:
        """
        Parse the classification response from the LLM.

        The AI returns text like:
            ```
            {"category": "invoices", "confidence": 0.95, "reasoning": "..."}
            ```

        Sometimes with extra text:
            ```
            Sure! Here is the classification:
            {"category": "invoices", "confidence": 0.95, "reasoning": "..."}
            I hope that helps!
            ```

        This method:
        1. Extracts JSON from response (finds { and })
        2. Parses JSON
        3. Validates category is in the allowed list
        4. Validates confidence is 0.0-1.0
        5. Creates ClassificationResult

        Args:
            response_text: Raw text from AI
            categories: Valid categories to check against

        Returns:
            Result containing:
                - Success: ClassificationResult
                - Failure: Error message

        Why extract JSON?
        - AI sometimes adds extra text before/after JSON
        - We only want the JSON part
        - Find first { and last }, extract what's between

        Why validate category?
        - AI might return "Invoices" when we want "invoices"
        - AI might return category not in our list
        - We normalize and validate

        Why validate confidence?
        - AI might return confidence > 1.0 or < 0.0
        - We clamp to valid range [0.0, 1.0]

        Example inputs and outputs:
            Input: {"category": "invoices", "confidence": 0.95, "reasoning": "..."}
            Output: ClassificationResult(category="invoices", confidence=0.95, ...)

            Input: "Sure! {"category": "INVOICE", "confidence": 1.5} Hope that helps!"
            Output: ClassificationResult(category="invoices", confidence=1.0, ...)

            Input: {"category": "unknown", "confidence": 0.8}
            Output: ClassificationResult(category="other", confidence=0.8, ...)
        """
        try:
            # Step 1: Extract JSON from response text
            #
            # Why extract?
            # - AI might add text before/after JSON
            # - Example: "Sure! {...} Hope that helps!"
            # - We only want the {...} part
            #
            # How?
            # - Find first occurrence of {
            # - Find last occurrence of }
            # - Extract everything between (inclusive)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                return Result.failure("No valid JSON found in response")

            json_text = response_text[json_start:json_end]

            # Step 2: Parse JSON string into Python dict
            parsed = json.loads(json_text)

            # Step 3: Extract classification fields
            #
            # Expected fields:
            # - category: string (required)
            # - confidence: float 0.0-1.0 (required)
            # - reasoning: string (optional)
            category = parsed.get("category", "").lower()  # Normalize to lowercase
            confidence = float(parsed.get("confidence", 0.0))
            reasoning = parsed.get("reasoning", "")

            # Step 4: Validate category is in allowed list
            #
            # Why validate?
            # - AI might return "Invoices" when categories = ["invoices"]
            # - AI might hallucinate category not in our list
            # - We need to map to valid category
            #
            # How?
            # - Convert all categories to lowercase
            # - Check if AI's category is in the list
            # - If not, default to "other" or first category
            category_lower = [c.lower() for c in categories]
            if category not in category_lower:
                # Category not valid, try to find best match or default
                category = "other" if "other" in category_lower else categories[0]
                logger.warning(f"Invalid category predicted, defaulting to: {category}")

            # Step 5: Validate confidence is in valid range
            #
            # Why validate?
            # - AI might return 1.5 or -0.2
            # - We need 0.0 ≤ confidence ≤ 1.0
            #
            # How?
            # - Clamp to [0.0, 1.0] using max(0, min(1.0, value))
            confidence = max(0.0, min(1.0, confidence))

            # Step 6: Create ClassificationResult
            #
            # Include metadata for debugging/auditing:
            # - Which model was used
            # - What temperature
            # - Raw response (for debugging)
            result = ClassificationResult(
                category=category,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    "model": self.model,
                    "temperature": self.temperature,
                    "raw_response": response_text,
                }
            )

            logger.info(f"Classification result: {category} (confidence: {confidence:.2f})")
            return Result.success(result)

        except json.JSONDecodeError as e:
            # JSON parsing failed
            # Common causes:
            # - AI didn't return valid JSON
            # - Malformed JSON (missing quotes, commas, etc.)
            error_msg = f"Failed to parse JSON response: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

        except (ValueError, TypeError) as e:
            # Type conversion failed (e.g., confidence not a number)
            error_msg = f"Invalid response format: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error parsing response: {e}"
            logger.error(error_msg)
            return Result.failure(error_msg)

    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================

    def get_available_models(self) -> List[str]:
        """
        Get list of available models from Ollama.

        Queries the /api/tags endpoint to see which models are installed.

        Returns:
            List of model names (e.g., ["llama3.2", "mistral", "codellama"])

        Example:
            >>> service = OllamaClassificationService()
            >>> models = service.get_available_models()
            >>> print("Available models:", models)
            Available models: ['llama3.2', 'mistral', 'llama3.2:13b']

        When to use:
        - During setup (check which models are available)
        - In UI (show user which models they can use)
        - For validation (check if configured model exists)

        Note: This is synchronous (not async) because it's typically
        called once during setup, not in hot path.
        """
        try:
            # Query Ollama's tags endpoint
            # Returns JSON like: {"models": [{"name": "llama3.2"}, ...]}
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            response.raise_for_status()

            # Extract model names from response
            models = response.json().get("models", [])
            return [model.get("name", "") for model in models if model.get("name")]

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []


# ==============================================================================
# FACTORY FUNCTION
# ==============================================================================

def create_ollama_service(config: ConfigurationProvider) -> OllamaClassificationService:
    """
    Factory function to create Ollama classification service from configuration.

    This is a factory pattern implementation:
    - Takes configuration as input
    - Creates and configures service
    - Returns ready-to-use service

    Benefits:
    - Centralized service creation
    - Easy to change implementation
    - Configuration management
    - Dependency Injection compatible

    Args:
        config: Configuration provider with settings

    Returns:
        Configured OllamaClassificationService

    Why use a factory?
    - Decouples service creation from usage
    - Easy to swap implementations (OpenAI, Claude, etc.)
    - Configuration stays in config files
    - Testable (can inject mock config)

    Example:
        ```python
        from config import Settings

        config = Settings()
        service = create_ollama_service(config)

        # Service is ready to use
        result = await service.classify_document(content, categories)
        ```

    Future enhancement:
    Add config parameters for:
    - ollama.host
    - ollama.model
    - ollama.temperature
    - ollama.timeout
    - ollama.max_tokens
    """
    # TODO: Get Ollama settings from config
    # For now, using sensible defaults
    #
    # Future: config.ollama.host, config.ollama.model, etc.
    return OllamaClassificationService(
        host="http://localhost:11434",
        model="llama3.2",
        timeout=120,
        temperature=0.1,     # Low for consistency
        max_tokens=1000,     # Enough for classification
    )
