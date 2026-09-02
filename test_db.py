import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings')
django.setup()
from django.db import connection

print("=== Buscando triggers en la tabla factura ===")
with connection.cursor() as c:
    # Listar triggers en tabla factura
    c.execute("""
        SELECT trigger_name, event_manipulation, action_statement
        FROM information_schema.triggers
        WHERE event_object_table = 'factura'
        ORDER BY trigger_name
    """)
    triggers = c.fetchall()
    if triggers:
        for t in triggers:
            print(f"  Trigger: {t[0]} | Evento: {t[1]} | Accion: {t[2][:80]}...")
    else:
        print("  No se encontraron triggers en la tabla factura")

    # Listar triggers en tabla corte_mensual
    c.execute("""
        SELECT trigger_name, event_manipulation, event_object_table
        FROM information_schema.triggers
        WHERE event_object_table IN ('factura', 'corte_mensual')
        ORDER BY event_object_table, trigger_name
    """)
    all_triggers = c.fetchall()
    print("\n=== Todos los triggers relacionados ===")
    for t in all_triggers:
        print(f"  {t[2]} -> {t[0]} ({t[1]})")

print("\n=== Eliminando triggers defectuosos ===")
with connection.cursor() as c:
    try:
        c.execute("DROP TRIGGER IF EXISTS trigger_actualizar_corte ON factura CASCADE")
        print("  trigger_actualizar_corte eliminado (si existía)")
    except Exception as e:
        print(f"  Error eliminando trigger_actualizar_corte: {e}")

    try:
        c.execute("DROP TRIGGER IF EXISTS actualizar_corte_mensual ON factura CASCADE")
        print("  actualizar_corte_mensual eliminado (si existía)")
    except Exception as e:
        print(f"  Error: {e}")

    try:
        c.execute("DROP FUNCTION IF EXISTS actualizar_corte_mensual_ajustador() CASCADE")
        print("  Función actualizar_corte_mensual_ajustador() eliminada (si existía)")
    except Exception as e:
        print(f"  Error eliminando función: {e}")

print("\nDone!")


from facturacion.models import Factura
from facturacion.serializers import FacturaSerializer

try:
    factura = Factura.objects.select_related('siniestro__aseguradora').get(pk=212)
    print("Factura encontrada:", factura.folio_factura, "estatus:", factura.estatus_factura)
    print("Siniestro:", factura.siniestro)
    print("Aseguradora obj:", factura.siniestro.aseguradora if factura.siniestro else None)

    # Simular aprobacion completa
    aseguradora_nombre = ''
    if factura.siniestro and factura.siniestro.aseguradora:
        aseguradora_nombre = (factura.siniestro.aseguradora.nombre or '').upper()
    print("Aseguradora nombre:", aseguradora_nombre)
    es_mapfre = 'MAPFRE' in aseguradora_nombre
    print("Es Mapfre:", es_mapfre)

    # Intentar el save
    original_estatus = factura.estatus_factura
    original_folio = factura.folio_factura
    original_fecha_pago = factura.fecha_pago

    factura.estatus_factura = 'PAGADA'
    factura.folio_factura = 'DIAG-TEST-001'
    factura.folio_reachcore = None
    factura.fecha_pago = datetime.date.today()
    factura.save()
    print("SAVE OK!")

    # Revertir
    factura.estatus_factura = original_estatus
    factura.folio_factura = original_folio
    factura.fecha_pago = original_fecha_pago
    factura.save()
    print("Revertido OK!")

    # Serializar
    s = FacturaSerializer(factura)
    d = s.data
    print("Serializer OK, aseguradora field:", d.get('aseguradora'))

except Exception as e:
    print("ERROR:")
    traceback.print_exc()

