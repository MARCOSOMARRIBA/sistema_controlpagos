from django.db import models
from siniestros.models import Siniestro, UsuarioCustom


class Factura(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_factura')
    folio_factura = models.CharField(max_length=100)
    fecha_emision = models.DateField()
    concepto = models.TextField()
    monto = models.DecimalField(max_digits=10, decimal_places=2, db_column='honorarios')
    siniestro = models.ForeignKey(Siniestro, models.DO_NOTHING, db_column='id_siniestro', related_name='facturas')

    # Campos adicionales de la BD
    tipo_factura = models.CharField(max_length=100, null=True, blank=True, default='SOLICITUD')
    gastos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    estatus_factura = models.CharField(max_length=100, null=True, blank=True, default='SOLICITADA')
    folio_reachcore = models.CharField(max_length=100, null=True, blank=True)
    fecha_pago = models.DateField(null=True, blank=True)
    id_ajustador = models.ForeignKey(UsuarioCustom, models.DO_NOTHING, db_column='id_ajustador', null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'factura'
        app_label = 'facturacion'  # Explícito para evitar RuntimeError con Python 3.13

    def __str__(self):
        return f'Factura {self.folio_factura} - Siniestro {self.siniestro_id}'
