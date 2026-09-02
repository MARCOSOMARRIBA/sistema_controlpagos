import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'siniestro';")
    cols = [row[0] for row in cursor.fetchall()]
    print("Columnas en siniestro:", cols)
