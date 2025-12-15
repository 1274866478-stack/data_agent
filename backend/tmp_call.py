import requests
import json

payload = {
    "query": "列出 products 表前 5 行",
    "enable_cache": False,
    "force_refresh": True
}

resp = requests.post("http://localhost:8000/api/v1/query", json=payload, timeout=30)
print(resp.status_code)
print(resp.text)


