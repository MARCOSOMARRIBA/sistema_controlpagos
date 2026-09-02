import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        nombres = ['Qualitas', 'GNP', 'MAPFRE', 'HDI', 'AXA', 'Zurich']
        
        for n in nombres:
            cursor.execute("INSERT INTO aseguradora (nombre, honorario_base, tarifa_km) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;", [n, 1500.00, 5.00])
        print(f"Se insertaron {len(nombres)} aseguradoras de prueba con éxito.")
except Exception as e:
    print(f"Error: {e}")
