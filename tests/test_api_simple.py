#!/usr/bin/env python3
"""
Simple API test to check search behavior
"""

import requests
import json
import time

def test_api_search():
    """Test the search API with different queries."""
    
    base_url = "http://localhost:8000"
    
    print("🔍 TESTING SEARCH API")
    print("=" * 40)
    
    # Check if API is running
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ API Health: {health_response.status_code}")
    except Exception as e:
        print(f"❌ API not accessible: {e}")
        print("💡 Make sure to start the backend: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    # Test queries
    test_queries = [
        ("acme", "Short query"),
        ("acme technical consulting code review and qa", "Long descriptive query")
    ]
    
    # Test different search modes
    search_modes = ["semantic", "keyword", "hybrid"]
    
    for query, description in test_queries:
        print(f"\n📝 {description}: '{query}'")
        print("-" * 60)
        
        for mode in search_modes:
            try:
                params = {
                    "q": query,
                    "mode": mode,
                    "limit": 5
                }
                
                start_time = time.time()
                response = requests.get(f"{base_url}/api/search", params=params, timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    print(f"  {mode.upper()}: {len(results)} results ({response_time:.0f}ms)")
                    
                    # Show top 2 results with scores
                    for i, result in enumerate(results[:2]):
                        filename = result.get("file_name", "unknown")
                        keyword_score = result.get("keyword_rank", 0)
                        semantic_score = result.get("semantic_rank", 0)
                        combined_score = result.get("combined_score", 0)
                        
                        print(f"    [{i+1}] {filename}")
                        if mode == "semantic":
                            print(f"        Semantic Score: {semantic_score:.6f}")
                        elif mode == "keyword":
                            print(f"        Keyword Score: {keyword_score:.6f}")
                        else:  # hybrid
                            print(f"        Keyword: {keyword_score:.6f}, Semantic: {semantic_score:.6f}, Combined: {combined_score:.6f}")
                
                else:
                    print(f"  {mode.upper()}: ERROR {response.status_code}")
                    error_text = response.text[:200] if response.text else "No error message"
                    print(f"    Error: {error_text}")
                    
            except Exception as e:
                print(f"  {mode.upper()}: FAILED - {e}")
    
    print(f"\n🎯 KEY FINDINGS:")
    print("Compare the semantic scores between short and long queries")
    print("The long query should get higher semantic scores for relevant documents")


if __name__ == "__main__":
    test_api_search()