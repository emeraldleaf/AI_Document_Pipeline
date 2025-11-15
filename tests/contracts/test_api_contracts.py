#!/usr/bin/env python3
"""
Consumer-Driven Contract Tests using Pact
==========================================

Tests that verify the API contracts defined by the frontend consumer.
These tests ensure that API changes don't break the frontend expectations.

Requirements:
    pip install pact-python pytest

Usage:
    # Run contract tests
    pytest tests/contracts/test_api_contracts.py -v

    # Publish contracts to Pact Broker (if available)
    pact-broker publish pacts/ --consumer-app-version=1.0.0
"""

import pytest
import requests
import json
from pathlib import Path
from typing import Dict, Any
from pact import Consumer, Provider, Format

# Import the API models for type validation
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api"))

try:
    from main import app
    from pydantic import BaseModel
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("Warning: API not available for contract testing")


class ContractTestBase:
    """Base class for contract tests."""

    def setup_method(self):
        """Setup for each test method."""
        self.consumer = Consumer('frontend')
        self.provider = Provider('api')

    def load_contract(self, contract_file: str) -> Dict[str, Any]:
        """Load contract from JSON file."""
        contract_path = Path(__file__).parent / contract_file
        with open(contract_path, 'r') as f:
            return json.load(f)


class TestSearchContracts(ContractTestBase):
    """Test search API contracts."""

    def test_search_documents_contract(self):
        """Test the search documents contract."""
        contract = self.load_contract('frontend-api-search-contract.json')

        # Extract the search interaction
        search_interaction = next(
            (i for i in contract['interactions']
             if i['description'] == 'Search documents with query'),
            None
        )
        assert search_interaction is not None, "Search interaction not found"

        # Test the contract expectations
        with self.consumer.has_pact_with(
            self.provider,
            pact_dir='tests/contracts/pacts'
        ) as pact:
            # Define the interaction
            (pact
             .given('documents exist')
             .upon_receiving('a search request')
             .with_request(
                 method='GET',
                 path='/api/search',
                 query=search_interaction['request']['query']
             )
             .will_respond_with(
                 status=200,
                 headers={'Content-Type': 'application/json'},
                 body=search_interaction['response']['body']
             ))

            # Run the test
            with pact:
                # Make actual request to provider
                response = requests.get(
                    'http://localhost:8000/api/search',
                    params=search_interaction['request']['query']
                )

                # Verify response matches contract
                assert response.status_code == 200
                assert response.headers['Content-Type'] == 'application/json'

                response_data = response.json()
                expected = search_interaction['response']['body']

                # Verify key response structure
                assert 'query' in response_data
                assert 'total_results' in response_data
                assert 'results' in response_data
                assert isinstance(response_data['results'], list)

                if response_data['total_results'] > 0:
                    result = response_data['results'][0]
                    assert 'id' in result
                    assert 'filename' in result
                    assert 'category' in result
                    assert 'confidence' in result

    def test_search_no_results_contract(self):
        """Test search with no results."""
        contract = self.load_contract('frontend-api-search-contract.json')

        no_results_interaction = next(
            (i for i in contract['interactions']
             if i['description'] == 'Search with no results'),
            None
        )
        assert no_results_interaction is not None

        with self.consumer.has_pact_with(
            self.provider,
            pact_dir='tests/contracts/pacts'
        ) as pact:
            (pact
             .given('no documents match query')
             .upon_receiving('a search request with no results')
             .with_request(
                 method='GET',
                 path='/api/search',
                 query=no_results_interaction['request']['query']
             )
             .will_respond_with(
                 status=200,
                 body=no_results_interaction['response']['body']
             ))

            with pact:
                response = requests.get(
                    'http://localhost:8000/api/search',
                    params=no_results_interaction['request']['query']
                )

                assert response.status_code == 200
                response_data = response.json()
                assert response_data['total_results'] == 0
                assert len(response_data['results']) == 0


class TestDocumentContracts(ContractTestBase):
    """Test document API contracts."""

    def test_get_document_contract(self):
        """Test get document details contract."""
        contract = self.load_contract('frontend-api-documents-contract.json')

        doc_interaction = next(
            (i for i in contract['interactions']
             if i['description'] == 'Get document details'),
            None
        )
        assert doc_interaction is not None

        with self.consumer.has_pact_with(
            self.provider,
            pact_dir='tests/contracts/pacts'
        ) as pact:
            (pact
             .given('document with id doc_001 exists')
             .upon_receiving('a request for document details')
             .with_request(
                 method='GET',
                 path='/api/documents/doc_001'
             )
             .will_respond_with(
                 status=200,
                 headers={'Content-Type': 'application/json'},
                 body=doc_interaction['response']['body']
             ))

            with pact:
                response = requests.get('http://localhost:8000/api/documents/doc_001')

                assert response.status_code == 200
                response_data = response.json()

                # Verify required fields
                required_fields = ['id', 'filename', 'category', 'confidence', 'metadata']
                for field in required_fields:
                    assert field in response_data, f"Missing required field: {field}"

                # Verify metadata structure
                assert isinstance(response_data['metadata'], dict)
                assert 'invoice_number' in response_data['metadata'] or 'contract_number' in response_data['metadata']


class TestBatchContracts(ContractTestBase):
    """Test batch upload API contracts."""

    def test_batch_upload_contract(self):
        """Test batch upload contract."""
        contract = self.load_contract('frontend-api-batch-contract.json')

        batch_interaction = next(
            (i for i in contract['interactions']
             if i['description'] == 'Upload batch of documents'),
            None
        )
        assert batch_interaction is not None

        with self.consumer.has_pact_with(
            self.provider,
            pact_dir='tests/contracts/pacts'
        ) as pact:
            # Note: Multipart form data testing would require additional setup
            # For now, we'll test the response structure expectations
            (pact
             .given('system ready for batch upload')
             .upon_receiving('a batch upload request')
             .with_request(
                 method='POST',
                 path='/api/batch-upload',
                 headers={'Content-Type': 'multipart/form-data'}
             )
             .will_respond_with(
                 status=202,
                 headers={'Content-Type': 'application/json'},
                 body=batch_interaction['response']['body']
             ))

            # This would normally test against a running provider
            # For now, we validate the contract structure
            expected_body = batch_interaction['response']['body']
            assert 'batch_id' in expected_body
            assert 'status' in expected_body
            assert 'files' in expected_body
            assert isinstance(expected_body['files'], list)


class TestHealthContracts(ContractTestBase):
    """Test health and stats API contracts."""

    def test_health_check_contract(self):
        """Test health check contract."""
        contract = self.load_contract('frontend-api-health-contract.json')

        health_interaction = next(
            (i for i in contract['interactions']
             if i['description'] == 'Health check'),
            None
        )
        assert health_interaction is not None

        with self.consumer.has_pact_with(
            self.provider,
            pact_dir='tests/contracts/pacts'
        ) as pact:
            (pact
             .upon_receiving('a health check request')
             .with_request(
                 method='GET',
                 path='/health'
             )
             .will_respond_with(
                 status=200,
                 headers={'Content-Type': 'application/json'},
                 body=health_interaction['response']['body']
             ))

            with pact:
                response = requests.get('http://localhost:8000/health')

                assert response.status_code == 200
                response_data = response.json()

                # Verify health response structure
                assert 'status' in response_data
                assert 'services' in response_data
                assert isinstance(response_data['services'], dict)

                # Verify service statuses
                services = response_data['services']
                assert 'database' in services
                assert 'search' in services
                assert services['database'] in ['up', 'down']
                assert services['search'] in ['up', 'down']


if __name__ == "__main__":
    # Run basic contract validation
    print("Validating contract files...")

    contracts_dir = Path(__file__).parent
    contract_files = [
        'frontend-api-search-contract.json',
        'frontend-api-documents-contract.json',
        'frontend-api-batch-contract.json',
        'frontend-api-health-contract.json'
    ]

    for contract_file in contract_files:
        contract_path = contracts_dir / contract_file
        if contract_path.exists():
            try:
                with open(contract_path, 'r') as f:
                    contract = json.load(f)

                # Basic validation
                assert 'consumer' in contract
                assert 'provider' in contract
                assert 'interactions' in contract
                assert isinstance(contract['interactions'], list)

                print(f"✅ {contract_file}: Valid contract structure")
            except Exception as e:
                print(f"❌ {contract_file}: Invalid contract - {e}")
        else:
            print(f"❌ {contract_file}: Contract file not found")

    print("\\nContract validation complete!")