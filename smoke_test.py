import os, time, subprocess, sys, urllib.request, json

# Lightweight local check. Run after installing dependencies and starting the server separately.
url = os.getenv("FINORA_TEST_URL","http://127.0.0.1:8000/api/health")
with urllib.request.urlopen(url, timeout=5) as r:
    data=json.load(r)
assert data.get("ok") is True
print("OK", data)
