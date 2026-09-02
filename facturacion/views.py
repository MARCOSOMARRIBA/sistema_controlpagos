from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from siniestros.permissions import IsAdminRole, IsAjustadorRole, get_user_role
from siniestros.models import Siniestro, UsuarioCustom, Gasto, Inspeccion
from .models import Factura
from .serializers import FacturaSerializer, FacturaCreateSerializer
import json
import datetime


class FacturaGuardarAPIView(APIView):
    """
    POST /api/facturacion/guardar/ — Endpoint avanzado para guardar factura + desglose de gastos.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        import traceback
        from django.db import IntegrityError

        data = request.data.copy()

        # Auto-asignar ajustador desde el usuario autenticado
        role = get_user_role(request.user)
        if role == 'AJUSTADOR':
            try:
                ajustador = UsuarioCustom.objects.get(username=request.user.username)
                data['id_ajustador'] = ajustador.id
            except UsuarioCustom.DoesNotExist:
                return Response({'error': 'Ajustador no encontrado en el sistema'}, status=status.HTTP_400_BAD_REQUEST)

        data['estatus_factura'] = 'SOLICITADA'

        # Auto-generar folio si no se proporcionó
        if not data.get('folio_factura'):
            from .models import Factura as FacturaModel
            ultimo_id = (FacturaModel.objects.order_by('-id').values_list('id', flat=True).first() or 0) + 1
            data['folio_factura'] = f'FAC-{ultimo_id:05d}'

        # Auto-asignar fecha de hoy si no se proporcionó
        if not data.get('fecha_emision'):
            import datetime
            data['fecha_emision'] = datetime.date.today().isoformat()

        serializer = FacturaCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            factura = serializer.save()
        except IntegrityError as e:
            err_msg = str(e)
            if 'folio_factura' in err_msg or 'unique' in err_msg.lower():
                return Response(
                    {'folio_factura': ['Ya existe una factura con este folio. Usa un folio diferente.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response({'error': f'Error de base de datos: {err_msg}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            return Response({'error': f'Error al guardar factura: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Intentar crear gastos si hay inspección asociada
        try:
            siniestro = factura.siniestro
            inspeccion = Inspeccion.objects.filter(id_siniestro=siniestro).first()
            desglose = request.data.get('desglose', {})
            gastos_creados = []

            if inspeccion and isinstance(desglose, dict):
                for tipo, monto in desglose.items():
                    try:
                        if monto and float(monto) > 0:
                            Gasto.objects.create(
                                tipo_gasto=str(tipo).upper()[:30],
                                monto=float(monto),
                                id_inspeccion=inspeccion,
                            )
                            gastos_creados.append(tipo)
                    except Exception:
                        pass  # No interrumpir si falla un gasto
        except Exception:
            pass  # Los gastos son opcionales, no deben bloquear la respuesta

        return Response(FacturaSerializer(factura).data, status=status.HTTP_201_CREATED)

class FacturasListAPIView(APIView):
    """
    GET  /api/facturacion/facturas/  — Listar facturas.
    POST /api/facturacion/facturas/  — Crear una factura nueva (solicitud).
    
    - ADMIN: ve todas las facturas.
    - AJUSTADOR: ve solo las facturas donde es el ajustador asignado.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = get_user_role(request.user)
        estatus_filter = request.query_params.get('estatus', None)

        if role == 'ADMIN':
            facturas = Factura.objects.select_related('siniestro', 'siniestro__aseguradora', 'id_ajustador').all()
        else:
            facturas = Factura.objects.select_related('siniestro', 'siniestro__aseguradora', 'id_ajustador').filter(
                id_ajustador__username=request.user.username
            )

        if estatus_filter:
            facturas = facturas.filter(estatus_factura=estatus_filter)

        facturas = facturas.order_by('-fecha_emision')
        serializer = FacturaSerializer(facturas, many=True)
        return Response(serializer.data)


    def post(self, request):
        data = request.data.copy()

        # Auto-asignar ajustador si es AJUSTADOR
        role = get_user_role(request.user)
        if role == 'AJUSTADOR':
            try:
                ajustador = UsuarioCustom.objects.get(username=request.user.username)
                data['id_ajustador'] = ajustador.id
            except UsuarioCustom.DoesNotExist:
                pass

        # Forzar estatus SOLICITADA en creación
        data['estatus_factura'] = 'SOLICITADA'

        serializer = FacturaCreateSerializer(data=data)
        if serializer.is_valid():
            factura = serializer.save()
            return Response(
                FacturaSerializer(factura).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacturaDetailAPIView(APIView):
    """
    GET   /api/facturacion/facturas/<pk>/  — Ver detalle de una factura.
    PATCH /api/facturacion/facturas/<pk>/  — Actualizar factura (ej. cambiar estatus, autorizar).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            return Factura.objects.select_related('siniestro', 'id_ajustador').get(pk=pk)
        except Factura.DoesNotExist:
            return None

    def get(self, request, pk):
        factura = self.get_object(pk)
        if not factura:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        # BUG-007: Verificar que un AJUSTADOR solo pueda ver sus propias facturas
        # Un ADMIN puede ver cualquier factura sin restricción
        role = get_user_role(request.user)
        if role == 'AJUSTADOR':
            if factura.id_ajustador and factura.id_ajustador.username != request.user.username:
                # Retornar 404 en lugar de 403 para no revelar que la factura existe (best practice)
                return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FacturaSerializer(factura)
        return Response(serializer.data)

    def patch(self, request, pk):
        factura = self.get_object(pk)
        if not factura:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        role = get_user_role(request.user)

        # Solo ADMIN puede cambiar el estatus (autorizar/rechazar)
        if 'estatus_factura' in request.data and role != 'ADMIN':
            return Response(
                {'error': 'Solo un administrador puede cambiar el estatus de la factura.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Un AJUSTADOR solo puede editar sus propias facturas en estatus PENDIENTE
        if role == 'AJUSTADOR':
            if factura.id_ajustador and factura.id_ajustador.username != request.user.username:
                return Response(
                    {'error': 'No tienes permiso para editar esta factura.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if factura.estatus_factura != 'SOLICITADA':
                return Response(
                    {'error': 'Solo puedes editar facturas en estatus SOLICITADA.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = FacturaCreateSerializer(factura, data=request.data, partial=True)
        if serializer.is_valid():
            factura = serializer.save()
            return Response(FacturaSerializer(factura).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AutorizarFacturaAPIView(APIView):
    """
    POST /api/facturacion/facturas/<pk>/autorizar/  — Aprobar una factura.
    Solo ADMIN puede autorizar.
    - Para aseguradoras Mapfre: folio_reachcore es obligatorio.
    - Para otras aseguradoras: solo numero_factura es obligatorio.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, pk):
        try:
            factura = Factura.objects.select_related('siniestro__aseguradora').get(pk=pk)
        except Factura.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if factura.estatus_factura != 'SOLICITADA':
            return Response(
                {'error': f'La factura ya tiene estatus: {factura.estatus_factura}. Solo se pueden autorizar facturas SOLICITADAS.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        numero_factura = request.data.get('numero_factura', '').strip()
        folio_reachcore = request.data.get('folio_reachcore', '').strip()

        if not numero_factura:
            return Response(
                {'error': 'El número de factura es obligatorio.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reachcore solo es obligatorio para aseguradoras Mapfre
        aseguradora_nombre = ''
        if factura.siniestro and factura.siniestro.aseguradora:
            aseguradora_nombre = (factura.siniestro.aseguradora.nombre or '').upper()

        es_mapfre = 'MAPFRE' in aseguradora_nombre

        if es_mapfre and not folio_reachcore:
            return Response(
                {'error': 'El folio Reachcore es obligatorio para facturas de Mapfre.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        factura.estatus_factura = 'PAGADA'
        factura.folio_factura = numero_factura
        factura.folio_reachcore = folio_reachcore if folio_reachcore else None
        factura.fecha_pago = datetime.date.today()
        factura.save()

        serializer = FacturaSerializer(factura)
        return Response({
            'message': f'Factura {factura.folio_factura} aprobada y marcada como PAGADA.',
            'factura': serializer.data
        })


class RechazarFacturaAPIView(APIView):
    """
    POST /api/facturacion/facturas/<pk>/rechazar/  — Rechazar una factura.
    Solo ADMIN puede rechazar.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk)
        except Factura.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if factura.estatus_factura != 'SOLICITADA':
            return Response(
                {'error': f'La factura tiene estatus: {factura.estatus_factura}. Solo se pueden rechazar facturas SOLICITADAS.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        factura.estatus_factura = 'RECHAZADA'
        factura.save()

        serializer = FacturaSerializer(factura)
        return Response({
            'message': f'Factura {factura.folio_factura} rechazada.',
            'factura': serializer.data
        })


class SiniestrosParaFacturaAPIView(APIView):
    """
    GET /api/facturacion/siniestros-disponibles/  — Lista siniestros para seleccionar al crear factura.
    - ADMIN: ve todos.
    - AJUSTADOR: ve solo los suyos.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = get_user_role(request.user)

        if role == 'ADMIN':
            siniestros = Siniestro.objects.select_related('ajustador').exclude(
                numero_siniestro__isnull=True
            ).exclude(numero_siniestro='')
        else:
            siniestros = Siniestro.objects.select_related('ajustador').filter(
                ajustador__username=request.user.username
            )

        data = [{
            'id': s.id,
            'numero_siniestro': s.numero_siniestro,
            'asegurado': s.asegurado or '',
            'ajustador': s.ajustador.username if s.ajustador else '',
            'gerente': s.gerente or 'ROBERTO MARQUEZ',
            'kilometros': s.kilometros or 0,
            'inspector': s.inspector or '',
            'fecha_inspeccion': s.fecha_inspeccion.strftime('%Y-%m-%d') if s.fecha_inspeccion else '',
            # El número de siniestro es la única referencia usada para pagos (folio y póliza no aplican)
            'label': f'Sin. {s.numero_siniestro} — {s.asegurado or "Sin asegurado"}'
        } for s in siniestros]

        return Response(data)


class FacturaStatsAPIView(APIView):
    """
    GET /api/facturacion/stats/  — Estadísticas de facturación.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = get_user_role(request.user)

        if role == 'ADMIN':
            qs = Factura.objects.all()
        else:
            qs = Factura.objects.filter(id_ajustador__username=request.user.username)

        total = qs.count()
        solicitadas = qs.filter(estatus_factura='SOLICITADA').count()
        pagadas = qs.filter(estatus_factura='PAGADA').count()
        rechazadas = qs.filter(estatus_factura='RECHAZADA').count()

        from django.db.models import Sum
        monto_total = qs.aggregate(total=Sum('monto'))['total'] or 0
        monto_pagado = qs.filter(estatus_factura='PAGADA').aggregate(total=Sum('monto'))['total'] or 0
        monto_solicitado = qs.filter(estatus_factura='SOLICITADA').aggregate(total=Sum('monto'))['total'] or 0

        return Response({
            'total': total,
            'pendientes': solicitadas,   # alias para compatibilidad frontend
            'aprobadas': pagadas,         # alias para compatibilidad frontend
            'rechazadas': rechazadas,
            'solicitadas': solicitadas,
            'pagadas': pagadas,
            'monto_total': float(monto_total),
            'monto_aprobado': float(monto_pagado),
            'monto_pagado': float(monto_pagado),
            'monto_pendiente': float(monto_solicitado),
        })
