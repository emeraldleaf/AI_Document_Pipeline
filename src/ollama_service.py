"""Ollama integration service for AI-powered document classification."""

import json
from typing import List, Dict, Any, Optional
import requests
from loguru import logger

from config import settings


class OllamaService:
    """Service for interacting with Ollama LLM for document classification."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        """Initialize Ollama service.

        Args:
            host: Ollama API host URL (defaults to settings)
            model: Model name to use (defaults to settings)
        """
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.api_url = f"{self.host}/api/generate"
        self.api_chat_url = f"{self.host}/api/chat"

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama service not available: {e}")
            return False

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [model.get("name") for model in models]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> Optional[str]:
        """Generate text using Ollama.

        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text or None if failed
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            if system_prompt:
                payload["system"] = system_prompt

            logger.debug(f"Sending request to Ollama: {self.model}")
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "").strip()

        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Ollama generation: {e}")
            return None

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> Optional[str]:
        """Chat with Ollama using message history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response or None if failed
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            logger.debug(f"Sending chat request to Ollama: {self.model}")
            response = requests.post(self.api_chat_url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            return result.get("message", {}).get("content", "").strip()

        except requests.exceptions.Timeout:
            logger.error("Ollama chat request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Ollama chat: {e}")
            return None

    def classify_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        categories: List[str],
    ) -> Optional[str]:
        """Classify a document into one of the predefined categories.

        Args:
            content: Document text content
            metadata: Document metadata dictionary
            categories: List of possible categories

        Returns:
            Classified category or None if failed
        """
        # Truncate content if too long (keep first and last parts)
        max_content_length = 4000
        if len(content) > max_content_length:
            half = max_content_length // 2
            content = content[:half] + "\n\n...[truncated]...\n\n" + content[-half:]

        # Build classification prompt
        system_prompt = """You are an expert document classifier. Your task is to analyze documents and classify them into the most appropriate category based on their content, structure, and metadata.

Be precise and consistent. Only respond with the category name, nothing else."""

        categories_str = ", ".join(categories)

        prompt = f"""Analyze the following document and classify it into ONE of these categories: {categories_str}

Document Metadata:
- File Name: {metadata.get('file_name', 'N/A')}
- File Type: {metadata.get('file_type', 'N/A')}
- Author: {metadata.get('author', 'N/A')}
- Title: {metadata.get('title', 'N/A')}
- Page Count: {metadata.get('page_count', 'N/A')}

Document Content:
{content}

Based on the content and metadata above, classify this document into the MOST appropriate category from the list.

Respond with ONLY the category name, nothing else. Choose from: {categories_str}

Category:"""

        try:
            result = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=50,
            )

            if not result:
                return None

            # Clean and validate the result
            category = result.strip().lower()

            # Try to match to one of the valid categories
            for valid_cat in categories:
                if valid_cat.lower() in category or category in valid_cat.lower():
                    logger.success(f"Classified as: {valid_cat}")
                    return valid_cat

            # If no exact match, return the first category (fallback)
            logger.warning(f"Could not match category '{result}', using fallback")
            return categories[-1] if "other" in categories[-1].lower() else categories[0]

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return None

    def classify_with_confidence(
        self,
        content: str,
        metadata: Dict[str, Any],
        categories: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Classify document and return category with confidence explanation.

        Args:
            content: Document text content
            metadata: Document metadata dictionary
            categories: List of possible categories

        Returns:
            Dict with category and reasoning, or None if failed
        """
        max_content_length = 4000
        if len(content) > max_content_length:
            half = max_content_length // 2
            content = content[:half] + "\n\n...[truncated]...\n\n" + content[-half:]

        system_prompt = """You are an expert document classifier. Analyze documents carefully and provide classification with reasoning.

Respond in JSON format with two fields:
- category: the chosen category name
- reasoning: brief explanation (1-2 sentences) why this category was chosen"""

        categories_str = ", ".join(categories)

        prompt = f"""Analyze this document and classify it into ONE category: {categories_str}

Document Metadata:
- File Name: {metadata.get('file_name', 'N/A')}
- File Type: {metadata.get('file_type', 'N/A')}
- Author: {metadata.get('author', 'N/A')}
- Title: {metadata.get('title', 'N/A')}

Document Content:
{content}

Respond ONLY with valid JSON:
{{"category": "chosen_category", "reasoning": "brief explanation"}}

JSON Response:"""

        try:
            result = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=150,
            )

            if not result:
                return None

            # Try to parse JSON response
            # Clean up common JSON formatting issues
            result = result.strip()
            if not result.startswith("{"):
                start = result.find("{")
                if start != -1:
                    result = result[start:]
            if not result.endswith("}"):
                end = result.rfind("}")
                if end != -1:
                    result = result[:end+1]

            response_data = json.loads(result)
            category = response_data.get("category", "").strip()
            reasoning = response_data.get("reasoning", "").strip()

            # Validate category
            matched_category = None
            for valid_cat in categories:
                if valid_cat.lower() in category.lower() or category.lower() in valid_cat.lower():
                    matched_category = valid_cat
                    break

            if not matched_category:
                matched_category = categories[-1] if "other" in categories[-1].lower() else categories[0]

            return {
                "category": matched_category,
                "reasoning": reasoning,
            }

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {result}")
            # Fallback to simple classification
            category = self.classify_document(content, metadata, categories)
            if category:
                return {"category": category, "reasoning": "Classification without reasoning"}
            return None
        except Exception as e:
            logger.error(f"Classification with confidence failed: {e}")
            return None
