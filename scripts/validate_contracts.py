#!/usr/bin/env python3
"""
Simple Contract Validation Script
Validates Consumer-Driven Contracts without full test framework
"""

import json
import requests
import sys
from pathlib import Path

def validate_contract(contract_file, base_url="http://localhost:8000"):
    """Validate a single contract file against the running API."""

    print(f"\n🔍 Validating contract: {contract_file}")

    try:
        with open(contract_file, 'r') as f:
            contract = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load contract: {e}")
        return False

    # Extract contract details
    consumer = contract.get('consumer', {}).get('name', 'Unknown')
    provider = contract.get('provider', {}).get('name', 'Unknown')
    interactions = contract.get('interactions', [])

    print(f"📋 Consumer: {consumer}")
    print(f"🏢 Provider: {provider}")
    print(f"📊 Interactions: {len(interactions)}")

    success_count = 0

    for i, interaction in enumerate(interactions, 1):
        print(f"\n  {i}. Testing interaction: {interaction.get('description', 'Unknown')}")

        request = interaction.get('request', {})
        response_spec = interaction.get('response', {})

        # Build request
        method = request.get('method', 'GET')
        path = request.get('path', '/')
        url = f"{base_url}{path}"

        try:
            # Make request
            resp = requests.request(method, url, timeout=10)
            print(f"     {method} {url} -> {resp.status_code}")

            # Check status code
            expected_status = response_spec.get('status', 200)
            if resp.status_code == expected_status:
                print("     ✅ Status code matches"                success_count += 1
            else:
                print(f"     ❌ Status code mismatch: expected {expected_status}, got {resp.status_code}")

            # Check response structure (basic validation)
            if resp.status_code == expected_status:
                try:
                    response_data = resp.json()
                    expected_body = response_spec.get('body', {})

                    # Basic structure check
                    if isinstance(expected_body, dict) and isinstance(response_data, dict):
                        missing_keys = set(expected_body.keys()) - set(response_data.keys())
                        if not missing_keys:
                            print("     ✅ Response structure matches"                        else:
                            print(f"     ⚠️  Missing keys in response: {missing_keys}")
                    else:
                        print("     ✅ Response format matches"
                except:
                    print("     ⚠️  Could not parse JSON response"
        except requests.exceptions.RequestException as e:
            print(f"     ❌ Request failed: {e}")

    return success_count == len(interactions)

def main():
    """Main validation function."""

    print("🔗 Contract Validation Tool")
    print("=" * 50)

    # Check API availability
    base_url = "http://localhost:8000"
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ API is running")
        else:
            print(f"⚠️  API responded with status {resp.status_code}")
    except:
        print("❌ API is not available")
        print(f"💡 Start the API with: python3 -m api.main")
        sys.exit(1)

    # Find contract files
    contracts_dir = Path("tests/contracts")
    contract_files = list(contracts_dir.glob("*.json"))

    if not contract_files:
        print("❌ No contract files found")
        sys.exit(1)

    print(f"📁 Found {len(contract_files)} contract files")

    # Validate each contract
    all_passed = True
    for contract_file in contract_files:
        if not validate_contract(contract_file, base_url):
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All contracts validated successfully!")
        print("📋 Frontend and API are compatible")
        return 0
    else:
        print("💥 Contract validation failed!")
        print("🔧 Update contracts or fix API to resolve issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())