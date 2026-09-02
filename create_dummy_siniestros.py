import os
import django
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()

from siniestros.models import Siniestro, Aseguradora, UsuarioCustom, CorteMensual
from decimal import Decimal

def poblar_datos():
    # Obtener usuarios (creados previamente por create_test_users.py)
    try:
        admin = UsuarioCustom.objects.get(username='admin')
        ajustador = UsuarioCustom.objects.get(username='ajustador1')
    except UsuarioCustom.DoesNotExist:
        print("Error: Los usuarios 'admin' y 'ajustador1' no existen. Ejecuta create_test_users.py primero.")
        return

    # Asegurar que existan aseguradoras
    aseguradoras = list(Aseguradora.objects.all())
    if not aseguradoras:
        Aseguradora.objects.create(nombre='Qualitas', honorario_base=1500)
        Aseguradora.objects.create(nombre='GNP', honorario_base=2000)
        aseguradoras = list(Aseguradora.objects.all())

    # Generar siniestros de prueba
    datos = [
        {'num': 'SIN-2026-001', 'pol': 'POL-111', 'aseg': 'Juan Perez', 'hon': '1500.00', 'usr': ajustador, 'estado': 'PENDIENTE'},
        {'num': 'SIN-2026-002', 'pol': 'POL-222', 'aseg': 'Maria Lopez', 'hon': '2350.50', 'usr': ajustador, 'estado': 'PENDIENTE'},
        {'num': 'SIN-2026-003', 'pol': 'POL-333', 'aseg': 'Carlos Slim', 'hon': '4000.00', 'usr': ajustador, 'estado': 'CONCLUIDO'},
        {'num': 'SIN-2026-004', 'pol': 'POL-444', 'aseg': 'Empresa SA de CV', 'hon': '8500.25', 'usr': admin, 'estado': 'PENDIENTE'},
        {'num': 'SIN-2026-005', 'pol': 'POL-555', 'aseg': 'Laura Gomez', 'hon': '1200.00', 'usr': admin, 'estado': 'CONCLUIDO'},
    ]

    # Eliminar siniestros que no tengan dependencias (ignoramos errores si hay facturas)
    try:
        # Intentar borrar los siniestros sin facturas asociadas primero
        for s in Siniestro.objects.all():
            try:
                s.delete()
            except:
                pass
        CorteMensual.objects.all().delete()
    except:
        pass
    print("Datos anteriores limpiados.")

    for d in datos:
        Siniestro.objects.create(
            numero_siniestro=d['num'],
            folio=f"FOL-{random.randint(1000,9999)}",
            poliza=d['pol'],
            aseguradora=random.choice(aseguradoras),
            gerente='ROBERTO MARQUEZ',
            ajustador=d['usr'],
            ramo='AUTOS',
            asegurado=d['aseg'],
            honorario=Decimal(d['hon']),
            fecha_ocurrido=datetime.now().date() - timedelta(days=random.randint(10, 50)),
            fecha_liquidacion=datetime.now().date() - timedelta(days=random.randint(1, 5)),
            estado_conclusion=d['estado']
        )
        
        # Acumular en corte mensual para el mes actual (2026-08)
        mes_actual = '2026-08'
        corte, _ = CorteMensual.objects.get_or_create(
            id_ajustador=d['usr'],
            mes_corte=mes_actual,
            defaults={'total_honorarios': Decimal('0'), 'monto_neto_pagado': Decimal('0'), 'total_anticipos_descontados': Decimal('0')}
        )
        corte.total_honorarios += Decimal(d['hon'])
        corte.monto_neto_pagado += Decimal(d['hon'])
        corte.save()

    print(f"¡Éxito! Se crearon {len(datos)} siniestros de prueba y se actualizaron los cortes mensuales.")

if __name__ == '__main__':
    poblar_datos()
