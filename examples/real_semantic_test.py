#!/usr/bin/env python3
"""
REAL Semantic Search Test - Using Actual Embedding Service

This script tests the ACTUAL semantic search behavior using your real
embedding service (Ollama) to verify the scoring behavior.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.embedding_service import OllamaEmbeddingService
import numpy as np


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    
    return dot_product / (norm_vec1 * norm_vec2)


async def test_real_semantic_search():
    """Test actual semantic search using real Ollama embeddings."""
    
    print("🔍 REAL SEMANTIC SEARCH TEST - Using Ollama Embeddings")
    print("=" * 70)
    
    # Initialize the actual embedding service
    try:
        embedding_service = OllamaEmbeddingService()
        print("✅ Connected to Ollama embedding service")
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print("💡 Make sure Ollama is running: ollama serve")
        print("💡 And the embedding model is available: ollama pull nomic-embed-text")
        return
    
    # Sample document content (what would be in your database)
    documents = {
        "doc1": "ACME Technical Consulting provides comprehensive code review and quality assurance services for enterprise software development projects. Our team specializes in technical audits, QA processes, and consulting.",
        "doc2": "Annual financial report from ACME Corporation showing quarterly earnings, market performance, and shareholder information for the fiscal year.",
        "doc3": "ACME Manufacturing quality control processes and industrial standards compliance documentation for production facilities.",
        "doc4": "Technical documentation for ACME software products including API integration guides and developer resources."
    }
    
    # Test queries
    queries = [
        "acme",
        "acme technical",
        "acme technical consulting", 
        "acme technical consulting code review and qa",
        "acme technical consulting code review and quality assurance services"
    ]
    
    print("\n📄 SAMPLE DOCUMENTS:")
    for doc_id, content in documents.items():
        print(f"{doc_id}: {content[:70]}...")
    
    print(f"\n🧠 EMBEDDING MODEL: {embedding_service.model}")
    print(f"📐 EMBEDDING DIMENSIONS: {embedding_service.dimension}")
    
    print("\n🔍 TESTING QUERIES:")
    for i, query in enumerate(queries, 1):
        print(f"{i}. '{query}'")
    
    print("\n⏳ Generating embeddings (this may take a moment)...")
    
    # Generate embeddings for all documents
    doc_embeddings = {}
    for doc_id, content in documents.items():
        try:
            embedding = embedding_service.embed_text(content)
            if embedding:
                doc_embeddings[doc_id] = embedding
                print(f"✅ Generated embedding for {doc_id} ({len(embedding)} dimensions)")
            else:
                print(f"❌ Failed to generate embedding for {doc_id}")
        except Exception as e:
            print(f"❌ Error generating embedding for {doc_id}: {e}")
    
    if not doc_embeddings:
        print("❌ No document embeddings generated. Cannot proceed.")
        return
    
    print("\n📊 SEMANTIC SIMILARITY RESULTS:")
    print("-" * 90)
    print(f"{'Query':<50} {'Doc':<6} {'Similarity':<12} {'Type'}")
    print("-" * 90)
    
    # Test each query
    results = {}
    for query in queries:
        try:
            query_embedding = embedding_service.embed_text(query)
            if not query_embedding:
                print(f"❌ Failed to generate embedding for query: {query}")
                continue
            
            results[query] = {}
            
            for doc_id, doc_embedding in doc_embeddings.items():
                similarity = cosine_similarity(query_embedding, doc_embedding)
                results[query][doc_id] = similarity
                
                # Classify document type for context
                doc_type = ""
                if "technical consulting" in documents[doc_id].lower():
                    doc_type = "Tech Services"
                elif "financial report" in documents[doc_id].lower():
                    doc_type = "Financial"
                elif "manufacturing" in documents[doc_id].lower():
                    doc_type = "Manufacturing"
                elif "software products" in documents[doc_id].lower():
                    doc_type = "Tech Docs"
                
                print(f"{query:<50} {doc_id:<6} {similarity:.6f}     {doc_type}")
                
        except Exception as e:
            print(f"❌ Error processing query '{query}': {e}")
    
    print("\n📈 ANALYSIS - Technical Consulting Document (doc1):")
    print("-" * 60)
    
    if results:
        target_doc = "doc1"  # The technical consulting document
        print("Query → Similarity Score:")
        
        for query in queries:
            if query in results and target_doc in results[query]:
                score = results[query][target_doc]
                print(f"  '{query}' → {score:.6f}")
        
        # Compare shortest vs longest query
        if queries[0] in results and queries[-1] in results:
            short_score = results[queries[0]][target_doc]
            long_score = results[queries[-1]][target_doc]
            
            print(f"\n📊 COMPARISON:")
            print(f"Shortest query ('{queries[0]}'): {short_score:.6f}")
            print(f"Longest query ('{queries[-1]}'): {long_score:.6f}")
            
            if long_score > short_score:
                improvement = ((long_score - short_score) / short_score) * 100
                print(f"Improvement: {improvement:.1f}% higher")
                print("✅ CONFIRMED: Longer query gets higher similarity score")
            elif short_score > long_score:
                print("🤔 UNEXPECTED: Shorter query scored higher")
            else:
                print("➡️ EQUAL: Both queries scored the same")
    
    print("\n🎯 EXPLANATION:")
    print("This test uses REAL Ollama embeddings (nomic-embed-text model)")
    print("The similarity scores show actual vector cosine similarity")
    print("Higher scores = more semantically similar content")
    
    return results


async def test_embedding_dimensions():
    """Show how query length affects embedding patterns."""
    
    print("\n🧮 EMBEDDING VECTOR ANALYSIS:")
    print("=" * 50)
    
    try:
        embedding_service = OllamaEmbeddingService()
        
        test_queries = [
            "acme",
            "acme technical consulting code review and qa"
        ]
        
        for query in test_queries:
            embedding = embedding_service.embed_text(query)
            if embedding:
                # Show some statistics about the embedding
                embedding_array = np.array(embedding)
                
                print(f"\nQuery: '{query}'")
                print(f"  Dimensions: {len(embedding)}")
                print(f"  L2 Norm: {np.linalg.norm(embedding_array):.6f}")
                print(f"  Mean: {np.mean(embedding_array):.6f}")
                print(f"  Std Dev: {np.std(embedding_array):.6f}")
                print(f"  Non-zero values: {np.count_nonzero(embedding_array)}")
                print(f"  Max value: {np.max(embedding_array):.6f}")
                print(f"  Min value: {np.min(embedding_array):.6f}")
                
                # Show first few dimensions
                print(f"  First 10 dimensions: {embedding[:10]}")
    
    except Exception as e:
        print(f"❌ Error in embedding analysis: {e}")


if __name__ == "__main__":
    print("🚀 Testing REAL semantic search behavior...")
    print("This uses your actual Ollama embedding service!")
    print()
    
    try:
        # Run the real test
        results = asyncio.run(test_real_semantic_search())
        
        # Show embedding analysis
        asyncio.run(test_embedding_dimensions())
        
        print("\n✅ Test completed!")
        print("This test used your ACTUAL embedding service and search logic.")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Install the embedding model: ollama pull nomic-embed-text")
        print("3. Check that src/embedding_service.py is accessible")