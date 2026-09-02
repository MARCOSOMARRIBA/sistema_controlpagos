from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Limpia todas las tablas de datos (factura, siniestro, inspeccion, gasto, anticipo, corte_mensual) manteniendo usuarios y aseguradoras.'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando limpieza de base de datos...')
        
        sql = """
            TRUNCATE TABLE factura, siniestro, inspeccion, gasto, anticipo, corte_mensual CASCADE;
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS('Limpieza completada exitosamente. Todas las tablas transaccionales han sido truncadas.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al limpiar la base de datos: {str(e)}'))
