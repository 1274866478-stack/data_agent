# -*- coding: utf-8 -*-
"""Debug Qdrant connection issue"""

import sys
import asyncio
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set UTF-8 encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=== Qdrant Connection Debug ===\n")

# Test 1: Using requests
print("1. Testing with requests library...")
try:
    import requests
    response = requests.get("http://localhost:6333/collections", timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Using httpx
print("\n2. Testing with httpx...")
try:
    import httpx
    async def test_httpx():
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:6333/collections", timeout=5.0)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:100]}")
    asyncio.run(test_httpx())
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Using qdrant_client with verbose
print("\n3. Testing with qdrant_client (verbose)...")
try:
    from qdrant_client import QdrantClient

    # Try with different connection methods
    print("   a) Using host+port:")
    try:
        client = QdrantClient(host="localhost", port=6333, check_compatibility=False)
        collections = client.get_collections()
        print(f"      Success! Collections: {len(collections.collections)}")
    except Exception as e:
        print(f"      Failed: {e}")

    print("\n   b) Using url:")
    try:
        client = QdrantClient(url="http://localhost:6333", check_compatibility=False)
        collections = client.get_collections()
        print(f"      Success! Collections: {len(collections.collections)}")
    except Exception as e:
        print(f"      Failed: {e}")

except Exception as e:
    print(f"   Import error: {e}")

print("\n=== Debug Complete ===")
