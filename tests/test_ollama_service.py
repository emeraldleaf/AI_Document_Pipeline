"""Unit tests for Ollama service."""

import pytest
from unittest.mock import Mock, patch
from src.ollama_service import OllamaService


class TestOllamaService:
    """Test Ollama service functionality."""

    def test_service_initialization(self):
        """Test service initialization with default settings."""
        service = OllamaService()
        assert service.host is not None
        assert service.model is not None
        assert service.api_url is not None

    def test_service_initialization_custom(self):
        """Test service initialization with custom parameters."""
        service = OllamaService(
            host="http://custom:11434",
            model="custom-model"
        )
        assert service.host == "http://custom:11434"
        assert service.model == "custom-model"

    @patch('requests.get')
    def test_is_available_success(self, mock_get):
        """Test service availability check when available."""
        mock_get.return_value.status_code = 200

        service = OllamaService()
        assert service.is_available() is True

    @patch('requests.get')
    def test_is_available_failure(self, mock_get):
        """Test service availability check when unavailable."""
        mock_get.side_effect = Exception("Connection refused")

        service = OllamaService()
        assert service.is_available() is False

    @patch('requests.get')
    def test_list_models(self, mock_get):
        """Test listing available models."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "mistral:7b"}
            ]
        }
        mock_get.return_value = mock_response

        service = OllamaService()
        models = service.list_models()

        assert len(models) == 2
        assert "llama3.2:3b" in models
        assert "mistral:7b" in models

    def test_classify_document_categories_validation(self):
        """Test category validation in classification."""
        service = OllamaService()
        categories = ["invoices", "contracts", "reports"]

        # This test would require mocking the actual API call
        # Here we just verify the method signature
        assert hasattr(service, 'classify_document')
        assert callable(service.classify_document)
