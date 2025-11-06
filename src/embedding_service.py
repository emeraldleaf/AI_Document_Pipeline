"""Embedding service with abstraction for easy POC → Production migration.

Supports:
- Ollama (free, local) for POC - NO additional dependencies required
- OpenAI API for production - Requires: pip install openai

The OpenAI package is an OPTIONAL dependency that is only imported when needed.
For local development with Ollama, no additional packages are required.
For production with OpenAI, install: pip install openai

Easy switching via configuration - just change EMBEDDING_PROVIDER in .env
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any
from enum import Enum

import requests
from loguru import logger


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"


class BaseEmbeddingService(ABC):
    """Base class for embedding services."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        pass


class OllamaEmbeddingService(BaseEmbeddingService):
    """Ollama embedding service (free, local).

    Uses nomic-embed-text model (768 dimensions).
    Perfect for POC and development.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dimension: int = 768
    ):
        """Initialize Ollama embedding service.

        Args:
            host: Ollama server URL
            model: Embedding model name
            dimension: Embedding dimension
        """
        self.host = host.rstrip("/")
        self.model = model
        self.dimension = dimension
        self._check_model_available()

    def _check_model_available(self):
        """Check if embedding model is available."""
        try:
            response = requests.get(f"{self.host}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]

                if self.model not in model_names:
                    logger.warning(
                        f"Embedding model '{self.model}' not found. "
                        f"Please run: ollama pull {self.model}"
                    )
                else:
                    logger.info(f"Ollama embedding model '{self.model}' ready")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding
        """
        try:
            response = requests.post(
                f"{self.host}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding", [])

                if len(embedding) != self.dimension:
                    logger.warning(
                        f"Expected {self.dimension} dimensions, got {len(embedding)}"
                    )

                return embedding
            else:
                logger.error(f"Ollama embedding failed: {response.status_code}")
                return [0.0] * self.dimension

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * self.dimension

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        embeddings = []
        for i, text in enumerate(texts):
            if i > 0 and i % 10 == 0:
                logger.debug(f"Generated {i}/{len(texts)} embeddings")

            embedding = self.embed_text(text)
            embeddings.append(embedding)

        return embeddings

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.dimension


class OpenAIEmbeddingService(BaseEmbeddingService):
    """OpenAI embedding service (paid, production).

    Uses text-embedding-3-small (1536 dimensions) or text-embedding-ada-002.
    Great for production with better quality and speed.

    Cost: ~$0.13 per 1M tokens (very affordable)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimension: int = 1536
    ):
        """Initialize OpenAI embedding service.

        Args:
            api_key: OpenAI API key
            model: Embedding model name
            dimension: Embedding dimension
        """
        self.api_key = api_key
        self.model = model
        self.dimension = dimension

        # Try to import openai (optional dependency for production use)
        try:
            import openai  # type: ignore[import-not-found]
            self.client = openai.OpenAI(api_key=api_key)
            logger.info(f"OpenAI embedding service initialized with {model}")
        except ImportError:
            logger.error(
                "OpenAI library not installed. "
                "Install with: pip install openai"
            )
            raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )

            embedding = response.data[0].embedding

            # Truncate to desired dimension if needed
            if len(embedding) > self.dimension:
                embedding = embedding[:self.dimension]

            return embedding

        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return [0.0] * self.dimension

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts using batch API.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embeddings
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model
                )

                batch_embeddings = [item.embedding for item in response.data]

                # Truncate if needed
                if self.dimension < len(batch_embeddings[0]):
                    batch_embeddings = [
                        emb[:self.dimension] for emb in batch_embeddings
                    ]

                all_embeddings.extend(batch_embeddings)

                logger.debug(f"Generated {len(all_embeddings)}/{len(texts)} embeddings")

            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
                # Return zero vectors for failed batch
                all_embeddings.extend([[0.0] * self.dimension] * len(batch))

        return all_embeddings

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.dimension


class EmbeddingService:
    """Factory for creating embedding services.

    Supports easy switching between providers via configuration.
    """

    @staticmethod
    def create(
        provider: EmbeddingProvider = EmbeddingProvider.OLLAMA,
        **kwargs
    ) -> BaseEmbeddingService:
        """Create an embedding service.

        Args:
            provider: Embedding provider to use
            **kwargs: Provider-specific arguments

        Returns:
            Embedding service instance

        Examples:
            # POC: Use Ollama (free)
            embeddings = EmbeddingService.create(
                provider=EmbeddingProvider.OLLAMA,
                host="http://localhost:11434"
            )

            # Production: Use OpenAI
            embeddings = EmbeddingService.create(
                provider=EmbeddingProvider.OPENAI,
                api_key="sk-..."
            )
        """
        if provider == EmbeddingProvider.OLLAMA:
            return OllamaEmbeddingService(**kwargs)

        elif provider == EmbeddingProvider.OPENAI:
            return OpenAIEmbeddingService(**kwargs)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def from_config(config) -> BaseEmbeddingService:
        """Create embedding service from configuration.

        Args:
            config: Configuration object with embedding settings

        Returns:
            Embedding service instance
        """
        provider = getattr(config, "embedding_provider", "ollama")

        if provider == "ollama":
            return OllamaEmbeddingService(
                host=getattr(config, "ollama_host", "http://localhost:11434"),
                model=getattr(config, "embedding_model", "nomic-embed-text"),
                dimension=getattr(config, "embedding_dimension", 768)
            )

        elif provider == "openai":
            api_key = getattr(config, "openai_api_key", None)
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable."
                )

            return OpenAIEmbeddingService(
                api_key=api_key,
                model=getattr(config, "embedding_model", "text-embedding-3-small"),
                dimension=getattr(config, "embedding_dimension", 1536)
            )

        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")


# Convenience function
def get_embedding_service(
    provider: str = "ollama",
    **kwargs
) -> BaseEmbeddingService:
    """Get an embedding service instance.

    Args:
        provider: "ollama" or "openai"
        **kwargs: Provider-specific arguments

    Returns:
        Embedding service instance
    """
    provider_enum = EmbeddingProvider(provider.lower())
    return EmbeddingService.create(provider=provider_enum, **kwargs)
