#!/usr/bin/env python3
"""
Debug: Compare App Results vs Test Results

This script will help us understand the difference between:
1. Your actual app running on localhost:3000 
2. The isolated test I ran

Let's check the exact search parameters and behavior.
"""

import requests
import json
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.embedding_service import OllamaEmbeddingService
from src.search_service import SearchService, SearchMode
import numpy as np


def test_app_api(base_url="http://localhost:8000"):
    """Test the actual API running on localhost."""
    
    print("🌐 TESTING ACTUAL APP API")
    print("=" * 50)
    
    # Test queries
    queries = [
        "acme",
        "acme technical consulting code review and qa"
    ]
    
    for query in queries:
        print(f"\n🔍 Testing query: '{query}'")
        
        # Test different search modes
        for mode in ["keyword", "semantic", "hybrid"]:
            try:
                url = f"{base_url}/api/search"
                params = {
                    "q": query,
                    "mode": mode,
                    "limit": 5
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    
                    print(f"  {mode.upper()}: {len(results)} results")
                    
                    # Show top result scores
                    for i, result in enumerate(results[:2]):
                        keyword_score = result.get("keyword_rank", 0)
                        semantic_score = result.get("semantic_rank", 0) 
                        combined_score = result.get("combined_score", 0)
                        
                        print(f"    [{i+1}] {result.get('file_name', 'unknown')}")
                        print(f"        Keyword: {keyword_score:.6f}")
                        print(f"        Semantic: {semantic_score:.6f}")  
                        print(f"        Combined: {combined_score:.6f}")
                
                else:
                    print(f"  {mode.upper()}: ERROR {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"  {mode.upper()}: FAILED - {e}")


def test_direct_search_service():
    """Test the search service directly (bypassing API)."""
    
    print("\n🔧 TESTING SEARCH SERVICE DIRECTLY")
    print("=" * 50)
    
    try:
        # Initialize services (same as in app)
        embedding_service = OllamaEmbeddingService()
        
        # You'll need to provide your database URL
        # This should match what's in your app
        database_url = "postgresql://your_user:your_password@localhost:5432/your_db"
        # Or check your config for the actual URL
        
        print("⚠️  Need database URL to test search service directly")
        print("Check your config.py or .env file for database connection")
        
        return None
        
    except Exception as e:
        print(f"❌ Failed to initialize search service: {e}")
        return None


def compare_embedding_generation():
    """Compare how embeddings are generated in isolation vs app."""
    
    print("\n🧠 COMPARING EMBEDDING GENERATION")
    print("=" * 50)
    
    try:
        embedding_service = OllamaEmbeddingService()
        
        test_queries = [
            "acme",
            "acme technical consulting code review and qa"
        ]
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            
            # Generate embedding
            embedding = embedding_service.embed_text(query)
            
            if embedding:
                embedding_array = np.array(embedding)
                print(f"  Dimensions: {len(embedding)}")
                print(f"  L2 Norm: {np.linalg.norm(embedding_array):.6f}")
                print(f"  First 5 values: {embedding[:5]}")
                
                # This should be identical to what the app uses
                print("  ✅ This should match what your app generates")
            else:
                print("  ❌ Failed to generate embedding")
                
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")


def check_app_status():
    """Check if the app is actually running and accessible."""
    
    print("🚀 CHECKING APP STATUS")
    print("=" * 30)
    
    endpoints_to_check = [
        "http://localhost:3000",  # Frontend
        "http://localhost:8000",  # Backend API
        "http://localhost:8000/health",  # Health check
    ]
    
    for endpoint in endpoints_to_check:
        try:
            response = requests.get(endpoint, timeout=5)
            print(f"✅ {endpoint}: Status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: Connection refused (not running?)")
        except requests.exceptions.Timeout:
            print(f"⏱️  {endpoint}: Timeout")
        except Exception as e:
            print(f"❓ {endpoint}: {e}")


def analyze_differences():
    """Analyze potential differences between test and app."""
    
    print("\n🔍 POTENTIAL DIFFERENCES ANALYSIS")
    print("=" * 40)
    
    print("Possible reasons for different results:")
    print()
    print("1. 📊 SEARCH MODE DEFAULTS:")
    print("   - My test: Pure semantic search")
    print("   - Your app: Hybrid search (keyword + semantic)")
    print("   - App default weights: keyword=0.6, semantic=0.4")
    print()
    print("2. 🗃️  DATABASE CONTENT:")
    print("   - My test: Simulated documents")
    print("   - Your app: Real documents in PostgreSQL")
    print("   - Different content = different scores")
    print()
    print("3. ⚙️  CONFIGURATION:")
    print("   - Different embedding models?")
    print("   - Different similarity thresholds?")
    print("   - Different preprocessing?")
    print()
    print("4. 🔄 CACHING:")
    print("   - App might cache embeddings/results")
    print("   - Test generates fresh embeddings")
    print()
    print("5. 📏 NORMALIZATION:")
    print("   - App might normalize scores differently")
    print("   - API response format might affect display")


if __name__ == "__main__":
    print("🕵️ DEBUGGING APP vs TEST DIFFERENCES")
    print("=" * 60)
    
    # Check basic connectivity
    check_app_status()
    
    # Test embedding generation (should be same)
    compare_embedding_generation()
    
    # Test the actual API 
    print("\n" + "="*60)
    print("⚠️  TESTING YOUR ACTUAL API:")
    print("Make sure your FastAPI backend is running on localhost:8000")
    print("Command: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")
    print("="*60)
    
    test_app_api()
    
    # Analyze potential differences
    analyze_differences()
    
    print("\n🎯 NEXT STEPS TO DEBUG:")
    print("1. Check what search mode your frontend is using (keyword/semantic/hybrid)")
    print("2. Look at actual API responses in browser dev tools")
    print("3. Check if app is using different embedding model/config")
    print("4. Verify the documents in your database")
    print("5. Test with the same exact documents I used in the test")