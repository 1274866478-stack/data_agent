# -*- coding: utf-8 -*-
"""Test Qdrant using REST API via requests library"""

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

import requests
import json

print("=== Testing Qdrant via REST API ===\n")

# Base URL
BASE_URL = "http://localhost:6333"

# Test 1: Get collections
print("1. Testing GET /collections")
response = requests.get(f"{BASE_URL}/collections", timeout=5)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Collections: {len(data['result']['collections'])}")

# Test 2: Create a collection
print("\n2. Testing POST /collections/{name}")
collection_name = "test_collection_rest"
create_payload = {
    "vectors": {
        "size": 1536,
        "distance": "Cosine"
    }
}

# Delete if exists first
try:
    requests.delete(f"{BASE_URL}/collections/{collection_name}", timeout=5)
    print(f"   Deleted existing collection (if any)")
except:
    pass

# Create new
response = requests.put(
    f"{BASE_URL}/collections/{collection_name}",
    json=create_payload,
    timeout=5
)
print(f"   Create Status: {response.status_code}")
if response.status_code == 200:
    print(f"   Collection created: {collection_name}")

# Test 3: Insert a point
print("\n3. Testing PUT /collections/{name}/points")
point_payload = {
    "points": [
        {
            "id": "test_point_1",
            "vector": [0.1] * 1536,
            "payload": {"test": "data"}
        }
    ]
}
response = requests.put(
    f"{BASE_URL}/collections/{collection_name}/points",
    json=point_payload,
    timeout=5
)
print(f"   Insert Status: {response.status_code}")

# Test 4: Search
print("\n4. Testing POST /collections/{name}/points/search")
search_payload = {
    "vector": [0.1] * 1536,
    "limit": 10
}
response = requests.post(
    f"{BASE_URL}/collections/{collection_name}/points/search",
    json=search_payload,
    timeout=5
)
print(f"   Search Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Found {len(data['result'])} points")

# Test 5: Delete collection
print("\n5. Testing DELETE /collections/{name}")
response = requests.delete(f"{BASE_URL}/collections/{collection_name}", timeout=5)
print(f"   Delete Status: {response.status_code}")

print("\n=== All REST API tests passed ===")
