import urllib.request
import urllib.parse
import json
import os

base_url = 'http://127.0.0.1:8000/api'

# 1. Login
data = json.dumps({'username': 'testajustador', 'password': 'testpass'}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/login/", data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print("Login status:", response.status)
        resp_data = json.loads(response.read().decode())
        token = resp_data.get('access')
        print("Token obtained")
except urllib.error.HTTPError as e:
    print("Login failed:", e.code, e.read().decode())
    exit(1)

# 2. Test importar
# Multipart form data manually
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.xlsx"\r\n'
    f"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
    f"dummy excel content\r\n"
    f"--{boundary}--\r\n"
).encode('utf-8')

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': f'multipart/form-data; boundary={boundary}',
    'Content-Length': len(body)
}

req_import = urllib.request.Request(f"{base_url}/siniestros/importar/", data=body, headers=headers)
try:
    with urllib.request.urlopen(req_import) as resp_import:
        print("Import status:", resp_import.status)
        print("Import response:", resp_import.read().decode())
except urllib.error.HTTPError as e:
    print("Import failed:", e.code, e.read().decode())

