
import chromadb
import sys
import logging

logging.basicConfig(level=logging.DEBUG)

print("Testing ChromaDB connection...")
try:
    client = chromadb.HttpClient(host='vector_db', port=8000)
    print(f"Client created: {client}")
    hb = client.heartbeat()
    print(f"Heartbeat: {hb}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
