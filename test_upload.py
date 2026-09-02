import pandas as pd
import urllib.request
import urllib.parse
import json
import io

df = pd.DataFrame([
    ['GERENTE', 'AJUSTADOR', 'NÚM. SINIESTRO', 'FOLIO', 'RAMO', 'ASEGURADO', 'HONORARIO (H)', 'RANGO'],
    ['Gerente A', 'testajustador', 'SIN-001', 'FOL-001', 'AUTOS', 'Juan Perez', 1500.0, 'Rango A']
])
excel_file = io.BytesIO()
with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='PRIMER AJUSTADORES', header=False, index=False)

excel_data = excel_file.getvalue()
base_url = 'http://127.0.0.1:8000/api'

# Login
data = json.dumps({'username': 'testadmin', 'password': 'testpass'}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/login/", data=data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as resp_login:
    resp_data = json.loads(resp_login.read().decode())
    token = resp_data.get('access')

# Importar
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.xlsx"\r\n'
    f"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
).encode('utf-8') + excel_data + f"\r\n--{boundary}--\r\n".encode('utf-8')

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': f'multipart/form-data; boundary={boundary}',
    'Content-Length': str(len(body))
}

req_import = urllib.request.Request(f"{base_url}/siniestros/importar/", data=body, headers=headers)
try:
    with urllib.request.urlopen(req_import) as resp_import:
        print("Import status:", resp_import.status)
        print("Import response:", resp_import.read().decode())
except urllib.error.HTTPError as e:
    print("Import failed:", e.code, e.read().decode())
