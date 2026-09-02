from django.db import models

class UsuarioCustom(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_usuario')
    username = models.CharField(max_length=100, unique=True, db_column='nombre')  # DB: VARCHAR(100)
    rol = models.CharField(max_length=20)  # DB: VARCHAR(20)
    factor_ajuste = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=1.0)
    
    class Meta:
        managed = False
        db_table = 'usuario'
        app_label = 'siniestros'

class Aseguradora(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_aseguradora')
    nombre = models.CharField(max_length=100)
    honorario_base = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarifa_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'aseguradora'
        app_label = 'siniestros'
        
    def __str__(self):
        return self.nombre

class Siniestro(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_siniestro')
    # DB: folio_reporte VARCHAR(50) NOT NULL — required, max 50 chars
    folio = models.CharField(max_length=50, unique=True, null=True, blank=True, db_column='folio_reporte')
    # DB: poliza VARCHAR(50) NOT NULL
    poliza = models.CharField(max_length=50, null=True, blank=True)
    # DB: num_siniestro VARCHAR(50) NOT NULL
    numero_siniestro = models.CharField(max_length=50, db_column='num_siniestro')
    # DB: id_aseguradora NOT NULL — must always have a value
    aseguradora = models.ForeignKey(Aseguradora, models.DO_NOTHING, db_column='id_aseguradora', null=True, blank=True)
    
    # Nuevos campos del Excel Avanzado
    gerente = models.CharField(max_length=150, null=True, blank=True)
    # DB: id_ajustador NOT NULL — must always have a value
    ajustador = models.ForeignKey(UsuarioCustom, models.DO_NOTHING, db_column='id_ajustador', null=True, blank=True)
    ramo = models.CharField(max_length=100, null=True, blank=True)
    asegurado = models.CharField(max_length=250, null=True, blank=True)
    fecha_ocurrido = models.DateField(null=True, blank=True)
    honorario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fecha_liquidacion = models.DateField(null=True, blank=True)
    dias = models.IntegerField(null=True, blank=True)
    rango = models.CharField(max_length=100, null=True, blank=True)
    
    # Datos Inspeccion antiguos y DB original
    fecha_inspeccion = models.DateField(null=True, blank=True)
    kilometros = models.IntegerField(null=True, blank=True)
    # DB: inspector VARCHAR(100) in siniestro table (not the inspeccion table)
    inspector = models.CharField(max_length=100, null=True, blank=True)
    # DB: estado_conclusion VARCHAR(30) NOT NULL
    estado_conclusion = models.CharField(max_length=30, null=False, blank=False, default='PENDIENTE')
    fecha_asignacion = models.DateField(null=True, blank=True, auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'siniestro'
        app_label = 'siniestros'


class CorteMensual(models.Model):
    id = models.AutoField(primary_key=True, db_column='id_cortemensual')
    id_ajustador = models.ForeignKey(UsuarioCustom, models.DO_NOTHING, db_column='id_ajustador')
    total_honorarios = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    total_anticipos_descontados = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    monto_neto_pagado = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    mes_corte = models.CharField(max_length=7, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'corte_mensual'
        unique_together = (('id_ajustador', 'mes_corte'),)
        app_label = 'siniestros'

class Inspeccion(models.Model):
    id_inspeccion = models.AutoField(primary_key=True)
    fecha_inspeccion = models.DateField()
    km_recorridos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    inspector = models.CharField(max_length=20, null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    viaticos = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    peajes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_pagar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    id_siniestro = models.ForeignKey('Siniestro', models.DO_NOTHING, db_column='id_siniestro')

    class Meta:
        managed = False
        db_table = 'inspeccion'
        app_label = 'siniestros'

class Gasto(models.Model):
    id_gasto = models.AutoField(primary_key=True)
    tipo_gasto = models.CharField(max_length=30)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    id_inspeccion = models.ForeignKey('Inspeccion', models.DO_NOTHING, db_column='id_inspeccion')

    class Meta:
        managed = False
        db_table = 'gasto'
        app_label = 'siniestros'

class Anticipo(models.Model):
    id_anticipo = models.AutoField(primary_key=True)
    id_ajustador = models.ForeignKey(UsuarioCustom, models.DO_NOTHING, db_column='id_ajustador')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_anticipo = models.DateField()
    motivo = models.CharField(max_length=255, null=True, blank=True)
    estado = models.CharField(max_length=50, default='PENDIENTE')

    class Meta:
        managed = False
        db_table = 'anticipo'
        app_label = 'siniestros'

