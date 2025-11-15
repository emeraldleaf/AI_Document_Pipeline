#!/usr/bin/env python3
"""Count valid embeddings"""
import json
import subprocess

result = subprocess.run(
    ['curl', '-s', 'http://localhost:9200/documents/_search?size=50'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)

valid = 0
invalid = 0

for hit in data['hits']['hits']:
    emb = hit['_source'].get('embedding', [])
    if emb and len(emb) > 0 and any(v != 0 for v in emb[:10]):
        valid += 1
    else:
        invalid += 1
        print(f"Invalid: {hit['_source']['file_name']}")

print(f"\n{'='*50}")
print(f"Valid embeddings: {valid}")
print(f"Invalid/missing embeddings: {invalid}")
print(f"Total documents: {valid + invalid}")
print(f"Success rate: {(valid/(valid+invalid)*100):.1f}%")
