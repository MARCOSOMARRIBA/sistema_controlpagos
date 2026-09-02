import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()
from django.db import connection

with open('../database_excel_maestro.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

with connection.cursor() as cursor:
    cursor.execute(sql)
print("Tabla archivo_excel_maestro creada exitosamente!")
