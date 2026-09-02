from rest_framework import serializers
from .models import Factura


class FacturaSerializer(serializers.ModelSerializer):
    ajustador_nombre = serializers.CharField(source='id_ajustador.username', read_only=True)
    numero_siniestro = serializers.CharField(source='siniestro.numero_siniestro', read_only=True)
    folio_siniestro = serializers.CharField(source='siniestro.folio', read_only=True)
    asegurado = serializers.CharField(source='siniestro.asegurado', read_only=True)
    gerente_siniestro = serializers.CharField(source='siniestro.gerente', read_only=True)
    # Nombre de aseguradora para detectar Mapfre en el frontend (modal de aprobación)
    aseguradora = serializers.SerializerMethodField()

    def get_aseguradora(self, obj):
        try:
            return obj.siniestro.aseguradora.nombre if obj.siniestro and obj.siniestro.aseguradora else ''
        except Exception:
            return ''

    class Meta:
        model = Factura
        fields = '__all__'


class FacturaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/solicitar una factura asociada a un siniestro existente."""

    class Meta:
        model = Factura
        fields = [
            'folio_factura', 'fecha_emision', 'concepto', 'monto',
            'siniestro', 'tipo_factura', 'gastos', 'id_ajustador',
            'estatus_factura',
        ]
        extra_kwargs = {
            'folio_factura': {'required': False, 'allow_blank': True, 'default': ''},
            'fecha_emision': {'required': False},
            'concepto': {'required': True},
            'monto': {'required': True},
            'siniestro': {'required': True},
        }
