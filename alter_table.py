import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()

from django.db import connection

queries = [
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS gerente VARCHAR(150);",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS ramo VARCHAR(100);",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS asegurado VARCHAR(250);",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS fecha_ocurrido DATE;",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS honorario DECIMAL(12,2);",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS fecha_liquidacion DATE;",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS dias INTEGER;",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS rango VARCHAR(100);",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS fecha_inspeccion DATE;",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS kilometros INTEGER;",
    "ALTER TABLE siniestro ADD COLUMN IF NOT EXISTS inspector VARCHAR(100);"
]

try:
    with connection.cursor() as cursor:
        for q in queries:
            cursor.execute(q)
        print("Se añadieron las columnas correctamente a la tabla 'siniestro'.")
except Exception as e:
    print(f"Error al alterar la tabla: {e}")
