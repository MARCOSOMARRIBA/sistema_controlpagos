from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from decimal import Decimal, InvalidOperation  # BUG-006: usar Decimal para evitar errores de punto flotante
from .models import Aseguradora, Siniestro, UsuarioCustom, CorteMensual, Gasto, Inspeccion
from .serializers import AseguradoraSerializer, SiniestroSerializer, CorteMensualSerializer
from .permissions import IsAdminRole, IsAjustadorRole, IsInspectorRole, IsAjustadorOrInspectorRole, get_user_role
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from django.core.management import call_command
from django.contrib.auth.models import User

class SiniestroCompletoSerializer(ModelSerializer):
    ajustador_nombre = serializers.CharField(source='ajustador.username', read_only=True)
    class Meta:
        model = Siniestro
        fields = '__all__'

class AseguradorasListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        aseguradoras = Aseguradora.objects.all()
        serializer = AseguradoraSerializer(aseguradoras, many=True)
        return Response(serializer.data)

class CargarSiniestroAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        data = request.data
        try:
            # Aseguradora — NOT NULL en DB, siempre necesita un valor
            aseguradora_id = data.get('aseguradora_id')
            if aseguradora_id:
                aseguradora = Aseguradora.objects.get(id=aseguradora_id)
            else:
                aseguradora = Aseguradora.objects.first()
                if not aseguradora:
                    aseguradora = Aseguradora.objects.create(nombre='Aseguradora General')
            
            # Ajustador — NOT NULL en DB
            ajustador_nombre = data.get('ajustador')
            if ajustador_nombre:
                ajustador_nombre_safe = str(ajustador_nombre).strip()[:100]  # DB: VARCHAR(100)
                ajustador_obj, _ = UsuarioCustom.objects.get_or_create(
                    username=ajustador_nombre_safe,
                    defaults={'rol': 'AJUSTADOR'}
                )
            else:
                ajustador_obj, _ = UsuarioCustom.objects.get_or_create(
                    username=request.user.username,
                    defaults={'rol': 'AJUSTADOR'}
                )
            
            # Truncar campos con límites estrictos en DB
            folio_raw = data.get('folio') or ''
            poliza_raw = data.get('poliza') or ''
            num_sin_raw = data.get('numero_siniestro') or ''
            inspector_raw = str(data.get('inspector') or '')[:100]  # siniestro.inspector VARCHAR(100)

            if not num_sin_raw:
                return Response({"error": "El número de siniestro es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

            siniestro = Siniestro.objects.create(
                folio=folio_raw[:50] if folio_raw else None,        # VARCHAR(50)
                poliza=poliza_raw[:50] if poliza_raw else None,     # VARCHAR(50)
                numero_siniestro=num_sin_raw[:50],                  # VARCHAR(50) NOT NULL
                aseguradora=aseguradora,
                ajustador=ajustador_obj,
                gerente=str(data.get('gerente') or '')[:150] or None,
                fecha_inspeccion=data.get('fecha_inspeccion') or None,
                kilometros=data.get('kilometros') or None,
                inspector=inspector_raw or None,
                estado_conclusion='PENDIENTE',                       # VARCHAR(30) NOT NULL
            )
            
            # Crear inspeccion automatica
            fecha_inspeccion = data.get('fecha_inspeccion')
            km = data.get('kilometros')
            inspector = data.get('inspector')
            if fecha_inspeccion or km or inspector:
                from .models import Inspeccion
                km_val = float(km) if km not in (None, '', 'null') else 0
                inspector_val = str(inspector or '')[:20]  # inspeccion.inspector VARCHAR(20)
                Inspeccion.objects.create(
                    id_siniestro=siniestro,
                    fecha_inspeccion=fecha_inspeccion or siniestro.fecha_asignacion or '2025-01-01',
                    km_recorridos=km_val,
                    inspector=inspector_val
                )
            
            return Response({"message": "Siniestro guardado exitosamente", "siniestro_id": siniestro.id}, status=status.HTTP_201_CREATED)
        except Aseguradora.DoesNotExist:
            return Response({"error": "Aseguradora no encontrada."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReporteAjustadoresAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    
    def get(self, request):
        siniestros = Siniestro.objects.select_related('ajustador', 'aseguradora').exclude(numero_siniestro__isnull=True).exclude(numero_siniestro='')
        
        data = []
        for s in siniestros:
            data.append({
                'id': s.id,
                'gerente': s.gerente or '',
                'ajustador': s.ajustador.username if s.ajustador else '',
                'folio': s.folio or '',
                'poliza': s.poliza or '',
                'ramo': s.ramo or '',
                'numero_siniestro': s.numero_siniestro,
                'aseguradora': s.aseguradora.nombre if s.aseguradora else '',
                'asegurado': s.asegurado or '',
                'fecha_ocurrido': s.fecha_ocurrido.strftime('%Y-%m-%d') if s.fecha_ocurrido else None,
                'honorario': float(s.honorario) if s.honorario else 0.0,
                'fecha_liquidacion': s.fecha_liquidacion.strftime('%Y-%m-%d') if s.fecha_liquidacion else None,
                'dias': s.dias,
                'rango': s.rango or '',
                'fecha_inspeccion': s.fecha_inspeccion.strftime('%Y-%m-%d') if s.fecha_inspeccion else None,
                'kilometros': s.kilometros,
                'inspector': s.inspector or '',
                'estado_conclusion': s.estado_conclusion or 'PENDIENTE',
                'fecha_asignacion': s.fecha_asignacion.strftime('%Y-%m-%d') if s.fecha_asignacion else None,
            })
            
        return Response(data)

class GerentesListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        gerentes = Siniestro.objects.exclude(gerente__isnull=True).exclude(gerente='').values_list('gerente', flat=True).distinct()
        return Response(list(gerentes))

class AjustadoresListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        ajustadores = UsuarioCustom.objects.filter(rol='AJUSTADOR').values_list('username', flat=True).distinct()
        return Response(list(ajustadores))

class UsuariosListCreateAPIView(APIView):
    """
    GET: Lista todos los usuarios con su rol.
    POST: Crea un nuevo usuario en auth.User y su correspondiente UsuarioCustom.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        usuarios_custom = UsuarioCustom.objects.all()
        django_users = User.objects.all()
        
        # Mapeamos usuarios de django para saber si existen o no
        django_users_map = {u.username: u for u in django_users}

        data = []
        for uc in usuarios_custom:
            u_django = django_users_map.get(uc.username)
            data.append({
                'id_custom': uc.id,
                'username': uc.username,
                'rol': uc.rol,
                'factor_ajuste': float(uc.factor_ajuste) if uc.factor_ajuste else 1.0,
                'tiene_acceso_sistema': bool(u_django),
                'is_active': u_django.is_active if u_django else False,
                'fecha_registro': u_django.date_joined.strftime('%Y-%m-%d %H:%M') if u_django else None,
            })
            
        return Response(data)

    @transaction.atomic
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        rol = request.data.get('rol', 'AJUSTADOR')

        if not username or not password:
            return Response({"error": "Username y Password son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Crear el usuario de Django (auth)
        try:
            user, created = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.save()
        except Exception as e:
            return Response({"error": f"Error al crear credenciales: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Crear o actualizar UsuarioCustom
        try:
            custom_user, _ = UsuarioCustom.objects.get_or_create(username=username, defaults={'rol': rol})
            if custom_user.rol != rol:
                custom_user.rol = rol
                custom_user.save()
        except Exception as e:
            return Response({"error": f"Error al asignar rol: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": f"Usuario {username} creado exitosamente con rol {rol}.",
            "username": username,
            "rol": rol
        }, status=status.HTTP_201_CREATED)

class CorteMensualAPIView(APIView):
    """
    GET /api/corte-mensual/
    Calcula dinámicamente el corte mensual basándose en facturas con estatus PAGADA.
    Agrupa por ajustador y mes, mostrando cuánto se le pagará a cada uno.
    Parámetros opcionales: ?mes=YYYY-MM  ?ajustador=nombre
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        from facturacion.models import Factura
        from django.db.models import Sum, Count

        mes_filter = request.query_params.get('mes', None)
        ajustador_filter = request.query_params.get('ajustador', None)

        # Facturas pagadas con datos de ajustador y siniestro
        qs = Factura.objects.select_related(
            'id_ajustador', 'siniestro'
        ).filter(estatus_factura='PAGADA')

        if ajustador_filter:
            qs = qs.filter(id_ajustador__username__icontains=ajustador_filter)

        if mes_filter:
            # Filtrar por mes YYYY-MM en fecha_pago
            try:
                anio, mes = mes_filter.split('-')
                qs = qs.filter(fecha_pago__year=int(anio), fecha_pago__month=int(mes))
            except (ValueError, AttributeError):
                pass

        # Agrupar manualmente por ajustador + mes
        from collections import defaultdict
        resumen = defaultdict(lambda: {
            'total_honorarios': 0.0,
            'total_gastos': 0.0,
            'total_anticipos_descontados': 0.0,
            'num_facturas': 0,
            'facturas': [],
        })

        meses_disponibles = set()

        for factura in qs:
            ajustador_nombre = factura.id_ajustador.username if factura.id_ajustador else 'Sin asignar'
            mes_pago = factura.fecha_pago.strftime('%Y-%m') if factura.fecha_pago else 'Sin fecha'
            key = (ajustador_nombre, mes_pago)
            meses_disponibles.add(mes_pago)

            r = resumen[key]
            r['ajustador_nombre'] = ajustador_nombre
            r['mes_corte'] = mes_pago
            r['total_honorarios'] += float(factura.monto or 0)
            r['total_gastos'] += float(factura.gastos or 0)
            r['num_facturas'] += 1
            r['facturas'].append({
                'id': factura.id,
                'folio': factura.folio_factura,
                'concepto': factura.concepto,
                'monto': float(factura.monto or 0),
                'gastos': float(factura.gastos or 0),
                'fecha_pago': factura.fecha_pago.strftime('%Y-%m-%d') if factura.fecha_pago else None,
                'folio_reachcore': factura.folio_reachcore or '',
            })

        # Obtener anticipos descontados de la tabla corte_mensual existente (si aplica)
        anticipos_map = {}
        try:
            cortes_bd = CorteMensual.objects.select_related('id_ajustador').all()
            for c in cortes_bd:
                k = (c.id_ajustador.username, c.mes_corte)
                anticipos_map[k] = float(c.total_anticipos_descontados or 0)
        except Exception:
            pass

        # Calcular inspecciones de aseguradoras solo_inspecciones (BBVA) por ajustador+mes
        inspecciones_map = {}
        try:
            insp_qs = Inspeccion.objects.select_related(
                'id_siniestro__ajustador', 'id_siniestro__aseguradora'
            ).filter(id_siniestro__aseguradora__solo_inspecciones=True)
            if ajustador_filter:
                insp_qs = insp_qs.filter(id_siniestro__ajustador__username__icontains=ajustador_filter)
            if mes_filter:
                try:
                    anio_i, mes_i = mes_filter.split('-')
                    insp_qs = insp_qs.filter(
                        fecha_inspeccion__year=int(anio_i), fecha_inspeccion__month=int(mes_i)
                    )
                except (ValueError, AttributeError):
                    pass

            for i in insp_qs:
                ajust_name = i.id_siniestro.ajustador.username if i.id_siniestro.ajustador else 'Sin asignar'
                mes_i_key = i.fecha_inspeccion.strftime('%Y-%m') if i.fecha_inspeccion else 'Sin fecha'
                k = (ajust_name, mes_i_key)
                if k not in inspecciones_map:
                    inspecciones_map[k] = {'total': 0.0, 'count': 0}
                inspecciones_map[k]['total'] += float(i.total_pagar or 0)
                inspecciones_map[k]['count'] += 1
                meses_disponibles.add(mes_i_key)
        except Exception:
            pass

        # Agregar entradas de inspecciones BBVA que no tienen facturas
        for (ajust_name, mes_key), insp_data in inspecciones_map.items():
            if (ajust_name, mes_key) not in resumen:
                resumen[(ajust_name, mes_key)]['ajustador_nombre'] = ajust_name
                resumen[(ajust_name, mes_key)]['mes_corte'] = mes_key

        resultado = []
        all_keys = set(resumen.keys()) | set(inspecciones_map.keys())
        for key in all_keys:
            ajustador_nombre, mes_pago = key
            r = resumen.get(key, {'total_honorarios': 0.0, 'total_gastos': 0.0, 'num_facturas': 0, 'facturas': []})
            anticipos = anticipos_map.get(key, 0.0)
            insp_data = inspecciones_map.get(key, {'total': 0.0, 'count': 0})
            total_inspecciones = insp_data['total']
            total_bruto = r['total_honorarios'] + r['total_gastos'] + total_inspecciones
            neto = total_bruto - anticipos
            resultado.append({
                'ajustador_nombre': ajustador_nombre,
                'mes_corte': mes_pago,
                'total_honorarios': round(r['total_honorarios'], 2),
                'total_gastos': round(r['total_gastos'], 2),
                'total_inspecciones_bbva': round(total_inspecciones, 2),
                'num_inspecciones_bbva': insp_data['count'],
                'total_bruto': round(total_bruto, 2),
                'total_anticipos_descontados': round(anticipos, 2),
                'monto_neto_pagado': round(neto, 2),
                'num_facturas': r['num_facturas'],
                'facturas': r['facturas'],
            })

        # Ordenar por mes desc, luego por ajustador
        resultado.sort(key=lambda x: (x['mes_corte'], x['ajustador_nombre']), reverse=True)

        return Response({
            'cortes': resultado,
            'meses_disponibles': sorted(meses_disponibles, reverse=True),
            'total_a_pagar': round(sum(r['monto_neto_pagado'] for r in resultado), 2),
        })


class LimpiarDatosAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    
    def post(self, request):
        try:
            call_command('reset_sistema')
            return Response({"status": "success", "message": "Sistema limpiado exitosamente."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MisSiniestrosAPIView(APIView):
    """
    GET /api/mis-siniestros/ — Lista los siniestros asignados al ajustador autenticado.
    FIX-006: Se filtra por UsuarioCustom.id en lugar de username directo para evitar
    desincronías entre auth.User.username y UsuarioCustom.username (columna 'nombre').
    """
    permission_classes = [permissions.IsAuthenticated, IsAjustadorRole]
    
    def get(self, request):
        # Buscar el UsuarioCustom correspondiente al usuario Django autenticado
        try:
            ajustador_custom = UsuarioCustom.objects.get(username=request.user.username)
        except UsuarioCustom.DoesNotExist:
            # El usuario autenticado no tiene entrada en la tabla 'usuario'
            # Esto significa que nunca se le asignaron siniestros correctamente.
            return Response({
                'warning': f'El usuario "{request.user.username}" no tiene perfil de ajustador en la base de datos. '
                           f'Contacta al administrador para que te asigne siniestros.',
                'siniestros': []
            })
        
        # FIX-006: Filtrar por FK directa (id) en vez de username — más robusto
        siniestros = Siniestro.objects.filter(ajustador=ajustador_custom)
        serializer = SiniestroSerializer(siniestros, many=True)
        return Response(serializer.data)

class MisGastosAPIView(APIView):
    def get(self, request):
        gastos = Gasto.objects.filter(id_ajustador__username=request.user.username)
        data = [{"id_gasto": g.id_gasto, "concepto": g.concepto, "monto": float(g.monto), "fecha_gasto": g.fecha_gasto} for g in gastos]
        return Response(data)

class CargarGridMasivoAPIView(APIView):
    """POST /api/cargar-grid-masivo/ - Recibe filas del grid copy-paste desde Excel con columnas dinámicas"""
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    # Mapeo fuzzy: palabras clave en el nombre de columna → campo del modelo Siniestro
    COLUMN_MAPPINGS = {
        'numero_siniestro': ['SINIESTRO', 'NUM_SINIESTRO', 'NO_SINIESTRO', 'NUMERO_SINIESTRO', 'N_SINIESTRO', 'NO.SINIESTRO', 'NOSINIESTRO', 'NUMSINIESTRO'],
        'gerente': ['GERENTE', 'GTE', 'GERENTE_REGIONAL'],
        'ajustador': ['AJUSTADOR', 'AJUST', 'NOMBRE_AJUSTADOR'],
        'folio': ['FOLIO', 'FOLIO_REPORTE', 'NO_FOLIO', 'NOFOLIO'],
        'poliza': ['POLIZA', 'NO_POLIZA', 'NUMERO_POLIZA', 'NUMPOLIZA', 'NOPOLIZA'],
        'ramo': ['RAMO', 'PRODUCTO', 'TIPO_RAMO'],
        'asegurado': ['ASEGURADO', 'NOMBRE_ASEGURADO', 'CLIENTE'],
        'honorario': ['HONOR', 'HONORARIO', 'HONORARIOS', 'TR_HONOR', 'TRHONOR', 'TR_HONORARIO', 'MONTO', 'IMPORTE'],
        'fecha_liquidacion': ['LIQUIDACION', 'FECHA_LIQUIDACION', 'FECHALIQUIDACION', 'FEC_LIQ', 'FECHA_LIQ'],
        'rango': ['RANGO', 'RANGO_DIAS'],
        'dias': ['DIAS', 'DIAS_TRANSCURRIDOS', 'DIAS_ATENCION'],
        'aseguradora': ['ASEGURADORA', 'CIA', 'COMPANIA', 'COMPAÑIA', 'EMPRESA'],
        'observaciones': ['OBSERVACIONES', 'OBSERVACION', 'NOTAS', 'COMENTARIOS'],
    }

    def _build_column_map(self, columnas):
        """
        Recibe la lista de columnas del frontend [{key, name}, ...] 
        y devuelve un dict: campo_db -> key_columna_excel
        """
        col_map = {}
        used_keys = set()

        for db_field, keywords in self.COLUMN_MAPPINGS.items():
            for col in columnas:
                if col['key'] in used_keys:
                    continue
                col_upper = col['key'].upper().replace(' ', '_').replace('.', '')
                col_name_upper = col.get('name', '').upper().replace(' ', '_').replace('.', '')
                
                for kw in keywords:
                    if kw in col_upper or kw in col_name_upper or col_upper in kw:
                        col_map[db_field] = col['key']
                        used_keys.add(col['key'])
                        break
                if db_field in col_map:
                    break

        return col_map

    def _get_val(self, fila, col_map, field, default=''):
        """Obtener valor de una fila usando el mapeo de columnas"""
        key = col_map.get(field)
        if not key:
            return default
        val = str(fila.get(key, default)).strip()
        return '' if val.lower() == 'nan' else val

    @transaction.atomic
    def post(self, request):
        filas = request.data.get('filas', [])
        columnas = request.data.get('columnas', [])
        mes_correspondiente = request.data.get('mes_correspondiente', '')

        if not filas:
            return Response({'error': 'No se enviaron filas.'}, status=status.HTTP_400_BAD_REQUEST)
        if not mes_correspondiente:
            return Response({'error': 'Se requiere mes_correspondiente.'}, status=status.HTTP_400_BAD_REQUEST)

        # Construir mapeo dinámico de columnas
        col_map = self._build_column_map(columnas)

        # Verificar que al menos encontró la columna de siniestro
        if 'numero_siniestro' not in col_map:
            return Response({
                'error': f'No se encontró una columna que corresponda al número de siniestro. Columnas recibidas: {[c["name"] for c in columnas]}. Asegúrate de incluir una columna con "SINIESTRO" en el nombre.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generar mapeo legible para mostrar al usuario
        mapeo_legible = {}
        for db_field, excel_key in col_map.items():
            col_info = next((c for c in columnas if c['key'] == excel_key), None)
            nombre_original = col_info['name'] if col_info else excel_key
            mapeo_legible[nombre_original] = db_field

        aseguradora_default = Aseguradora.objects.first()
        if not aseguradora_default:
            aseguradora_default = Aseguradora.objects.create(nombre='Aseguradora General')

        # Buscar aseguradora por nombre si viene en los datos
        def get_aseguradora(nombre):
            if not nombre:
                return aseguradora_default
            aseg = Aseguradora.objects.filter(nombre__icontains=nombre).first()
            return aseg or aseguradora_default

        ajustador_default, _ = UsuarioCustom.objects.get_or_create(
            username='sin_asignar',
            defaults={'rol': 'AJUSTADOR'}
        )

        insertados = 0
        actualizados = 0
        errores = []
        warnings = []  # BUG-008: registrar campos con datos inválidos (fallo silencioso)

        for idx, fila in enumerate(filas):
            try:
                num_siniestro = self._get_val(fila, col_map, 'numero_siniestro')
                if not num_siniestro:
                    continue

                # Buscar/crear ajustador
                ajustador_nombre = self._get_val(fila, col_map, 'ajustador')
                usuario_ajustador = ajustador_default
                if ajustador_nombre:
                    usuario_ajustador, _ = UsuarioCustom.objects.get_or_create(
                        username=ajustador_nombre,
                        defaults={'rol': 'AJUSTADOR'}
                    )

                # Parsear honorario
                honorario_raw = self._get_val(fila, col_map, 'honorario', '0').replace(',', '').replace('$', '').strip()
                try:
                    honorario_val = Decimal(honorario_raw) if honorario_raw else Decimal('0')  # BUG-006: usar Decimal
                except (ValueError, TypeError, InvalidOperation):
                    # BUG-008: registrar warning en lugar de fallar silenciosamente
                    warnings.append({
                        'fila': idx + 1,
                        'campo': 'honorario',
                        'valor_original': honorario_raw,
                        'accion': 'Se importó como $0.00 por valor no numérico'
                    })
                    honorario_val = Decimal('0')

                # Parsear fecha liquidacion
                fecha_liq = None
                fecha_liq_raw = self._get_val(fila, col_map, 'fecha_liquidacion')
                if fecha_liq_raw:
                    try:
                        from datetime import datetime
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S', '%d-%m-%Y'):
                            try:
                                fecha_liq = datetime.strptime(fecha_liq_raw[:19], fmt).date()
                                break
                            except ValueError:
                                continue
                        # BUG-008: si ningún formato funcionó, registrar warning
                        if fecha_liq is None:
                            warnings.append({
                                'fila': idx + 1,
                                'campo': 'fecha_liquidacion',
                                'valor_original': fecha_liq_raw,
                                'accion': 'Se importó como NULL por formato de fecha no reconocido'
                            })
                    except Exception:
                        warnings.append({
                            'fila': idx + 1,
                            'campo': 'fecha_liquidacion',
                            'valor_original': fecha_liq_raw,
                            'accion': 'Se importó como NULL por error al parsear la fecha'
                        })

                # Aseguradora
                aseg_nombre = self._get_val(fila, col_map, 'aseguradora')
                aseguradora = get_aseguradora(aseg_nombre)

                # Ver honorario anterior para delta (BUG-006: usar Decimal para evitar errores de float)
                siniestro_obj = Siniestro.objects.filter(numero_siniestro=num_siniestro).first()
                honorario_anterior = siniestro_obj.honorario if (siniestro_obj and siniestro_obj.honorario) else Decimal('0')

                # Truncar campos a límites exactos de la DB
                siniestro, created = Siniestro.objects.update_or_create(
                    numero_siniestro=num_siniestro[:50],  # VARCHAR(50)
                    defaults={
                        'gerente': (self._get_val(fila, col_map, 'gerente') or '')[:150] or None,
                        'ajustador': usuario_ajustador,
                        'aseguradora': aseguradora,
                        'folio': (self._get_val(fila, col_map, 'folio') or '')[:50] or None,   # VARCHAR(50)
                        'poliza': (self._get_val(fila, col_map, 'poliza') or '')[:50] or None, # VARCHAR(50)
                        'ramo': (self._get_val(fila, col_map, 'ramo') or '')[:100] or None,
                        'asegurado': (self._get_val(fila, col_map, 'asegurado') or '')[:250] or None,
                        'honorario': honorario_val,
                        'fecha_liquidacion': fecha_liq,
                        'rango': (self._get_val(fila, col_map, 'rango') or '')[:100] or None,
                        'estado_conclusion': 'PENDIENTE',  # VARCHAR(30) NOT NULL
                    }
                )

                if created:
                    insertados += 1
                else:
                    actualizados += 1

                # BUG-006: Acumular en CorteMensual con aritmética Decimal (evita errores de punto flotante)
                diferencia = honorario_val - honorario_anterior  # Ambos son Decimal ahora
                if diferencia != Decimal('0'):
                    corte, _ = CorteMensual.objects.get_or_create(
                        id_ajustador=usuario_ajustador,
                        mes_corte=mes_correspondiente,
                        defaults={'total_honorarios': Decimal('0'), 'monto_neto_pagado': Decimal('0'), 'total_anticipos_descontados': Decimal('0')}
                    )
                    # BUG-006: Operar directamente con Decimal del ORM — sin convertir a float
                    corte.total_honorarios = corte.total_honorarios + diferencia
                    corte.monto_neto_pagado = corte.monto_neto_pagado + diferencia
                    corte.save()

            except Exception as e:
                errores.append({'fila': idx + 1, 'error': str(e)})

        return Response({
            'status': 'success',
            'message': f'Carga completada: {insertados} nuevos, {actualizados} actualizados.',
            'insertados': insertados,
            'actualizados': actualizados,
            'errores_count': len(errores),
            'errores': errores[:20],
            # BUG-008: incluir warnings de campos con datos inválidos
            'warnings_count': len(warnings),
            'warnings': warnings[:50],
            'mapeo_usado': mapeo_legible,
        }, status=status.HTTP_201_CREATED)


class CargarSiniestrosAjustadorAPIView(APIView):
    """
    POST /api/ajustador/cargar-siniestros/
    FIX-003: Permite al AJUSTADOR cargar su cartera desde un copy-paste de Excel.
    SEGURIDAD: El campo 'ajustador' en el Excel es IGNORADO. El backend SIEMPRE
    asigna el id_ajustador del usuario autenticado, evitando suplantación.
    """
    permission_classes = [permissions.IsAuthenticated, IsAjustadorRole]

    # Reutilizamos los mismos mapeos del endpoint Admin
    COLUMN_MAPPINGS = CargarGridMasivoAPIView.COLUMN_MAPPINGS

    def _build_column_map(self, columnas):
        return CargarGridMasivoAPIView._build_column_map(self, columnas)

    def _get_val(self, fila, col_map, field, default=''):
        return CargarGridMasivoAPIView._get_val(self, fila, col_map, field, default)

    @transaction.atomic
    def post(self, request):
        filas = request.data.get('filas', [])
        columnas = request.data.get('columnas', [])
        mes_correspondiente = request.data.get('mes_correspondiente', '')

        if not filas:
            return Response({'error': 'No se enviaron filas.'}, status=status.HTTP_400_BAD_REQUEST)
        if not mes_correspondiente:
            return Response({'error': 'Se requiere mes_correspondiente.'}, status=status.HTTP_400_BAD_REQUEST)

        # FIX-003: Obtener/crear el UsuarioCustom del ajustador autenticado
        # El Excel puede incluir una columna 'ajustador' pero será IGNORADA
        try:
            ajustador_autenticado = UsuarioCustom.objects.get(username=request.user.username)
        except UsuarioCustom.DoesNotExist:
            # Crear el perfil si no existe (primera vez del ajustador)
            ajustador_autenticado, _ = UsuarioCustom.objects.get_or_create(
                username=request.user.username,
                defaults={'rol': 'AJUSTADOR'}
            )

        col_map = self._build_column_map(columnas)

        if 'numero_siniestro' not in col_map:
            return Response({
                'error': f'No se encontró columna de número de siniestro. Columnas recibidas: {[c["name"] for c in columnas]}'
            }, status=status.HTTP_400_BAD_REQUEST)

        mapeo_legible = {}
        for db_field, excel_key in col_map.items():
            col_info = next((c for c in columnas if c['key'] == excel_key), None)
            nombre_original = col_info['name'] if col_info else excel_key
            mapeo_legible[nombre_original] = db_field

        aseguradora_default = Aseguradora.objects.first()
        if not aseguradora_default:
            aseguradora_default = Aseguradora.objects.create(nombre='Aseguradora General')

        def get_aseguradora(nombre):
            if not nombre:
                return aseguradora_default
            return Aseguradora.objects.filter(nombre__icontains=nombre).first() or aseguradora_default

        insertados = 0
        actualizados = 0
        errores = []
        warnings = []

        for idx, fila in enumerate(filas):
            try:
                num_siniestro = self._get_val(fila, col_map, 'numero_siniestro')
                if not num_siniestro:
                    continue

                # Parsear honorario
                honorario_raw = self._get_val(fila, col_map, 'honorario', '0').replace(',', '').replace('$', '').strip()
                try:
                    honorario_val = Decimal(honorario_raw) if honorario_raw else Decimal('0')
                except (ValueError, TypeError, InvalidOperation):
                    warnings.append({'fila': idx + 1, 'campo': 'honorario', 'valor_original': honorario_raw, 'accion': 'Se importó como $0.00'})
                    honorario_val = Decimal('0')

                # Parsear fecha liquidacion
                fecha_liq = None
                fecha_liq_raw = self._get_val(fila, col_map, 'fecha_liquidacion')
                if fecha_liq_raw:
                    try:
                        from datetime import datetime
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S', '%d-%m-%Y'):
                            try:
                                fecha_liq = datetime.strptime(fecha_liq_raw[:19], fmt).date()
                                break
                            except ValueError:
                                continue
                        if fecha_liq is None:
                            warnings.append({'fila': idx + 1, 'campo': 'fecha_liquidacion', 'valor_original': fecha_liq_raw, 'accion': 'Se importó como NULL'})
                    except Exception:
                        warnings.append({'fila': idx + 1, 'campo': 'fecha_liquidacion', 'valor_original': fecha_liq_raw, 'accion': 'Error al parsear'})

                aseg_nombre = self._get_val(fila, col_map, 'aseguradora')
                aseguradora = get_aseguradora(aseg_nombre)

                siniestro_obj = Siniestro.objects.filter(numero_siniestro=num_siniestro).first()
                honorario_anterior = siniestro_obj.honorario if (siniestro_obj and siniestro_obj.honorario) else Decimal('0')

                # FIX-003: SIEMPRE usar el ajustador autenticado — ignorar columna del Excel
                # Truncar campos a límites exactos de la DB
                siniestro, created = Siniestro.objects.update_or_create(
                    numero_siniestro=num_siniestro[:50],  # VARCHAR(50)
                    defaults={
                        'gerente': (self._get_val(fila, col_map, 'gerente') or '')[:150] or None,
                        'ajustador': ajustador_autenticado,  # <-- FORZADO al usuario autenticado
                        'aseguradora': aseguradora,
                        'folio': (self._get_val(fila, col_map, 'folio') or '')[:50] or None,   # VARCHAR(50)
                        'poliza': (self._get_val(fila, col_map, 'poliza') or '')[:50] or None, # VARCHAR(50)
                        'ramo': (self._get_val(fila, col_map, 'ramo') or '')[:100] or None,
                        'asegurado': (self._get_val(fila, col_map, 'asegurado') or '')[:250] or None,
                        'honorario': honorario_val,
                        'fecha_liquidacion': fecha_liq,
                        'rango': (self._get_val(fila, col_map, 'rango') or '')[:100] or None,
                        'estado_conclusion': 'PENDIENTE',  # VARCHAR(30) NOT NULL
                    }
                )

                if created:
                    insertados += 1
                else:
                    actualizados += 1

                # Acumular en CorteMensual
                diferencia = honorario_val - honorario_anterior
                if diferencia != Decimal('0'):
                    corte, _ = CorteMensual.objects.get_or_create(
                        id_ajustador=ajustador_autenticado,
                        mes_corte=mes_correspondiente,
                        defaults={'total_honorarios': Decimal('0'), 'monto_neto_pagado': Decimal('0'), 'total_anticipos_descontados': Decimal('0')}
                    )
                    corte.total_honorarios = corte.total_honorarios + diferencia
                    corte.monto_neto_pagado = corte.monto_neto_pagado + diferencia
                    corte.save()

            except Exception as e:
                errores.append({'fila': idx + 1, 'error': str(e)})

        return Response({
            'status': 'success',
            'message': f'Carga completada: {insertados} nuevos, {actualizados} actualizados.',
            'ajustador_asignado': ajustador_autenticado.username,
            'insertados': insertados,
            'actualizados': actualizados,
            'errores_count': len(errores),
            'errores': errores[:20],
            'warnings_count': len(warnings),
            'warnings': warnings[:50],
            'mapeo_usado': mapeo_legible,
        }, status=status.HTTP_201_CREATED)


class SiniestroInspeccionesAPIView(APIView):
    """
    GET  /api/siniestros/<id>/inspecciones/  — Lista las inspecciones de un siniestro.
    POST /api/siniestros/<id>/inspecciones/  — Agrega una nueva inspección al siniestro.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, siniestro_id):
        try:
            siniestro = Siniestro.objects.get(pk=siniestro_id)
        except Siniestro.DoesNotExist:
            return Response({'error': 'Siniestro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        inspecciones = Inspeccion.objects.filter(id_siniestro=siniestro).order_by('fecha_inspeccion')
        data = [{
            'id': i.id_inspeccion,
            'fecha_inspeccion': i.fecha_inspeccion.strftime('%Y-%m-%d') if i.fecha_inspeccion else None,
            'km_recorridos': float(i.km_recorridos) if i.km_recorridos else 0,
            'inspector': i.inspector or '',
            'costo': float(i.costo) if i.costo else 0,
            'viaticos': float(i.viaticos) if i.viaticos else 0,
            'peajes': float(i.peajes) if i.peajes else 0,
            'total_pagar': float(i.total_pagar) if i.total_pagar else 0,
        } for i in inspecciones]
        return Response(data)

    @transaction.atomic
    def post(self, request, siniestro_id):
        import traceback
        try:
            siniestro = Siniestro.objects.get(pk=siniestro_id)
        except Siniestro.DoesNotExist:
            return Response({'error': 'Siniestro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        fecha = request.data.get('fecha_inspeccion')
        km = request.data.get('km_recorridos', 0)
        costo = request.data.get('costo', 0)
        viaticos = request.data.get('viaticos', 0)
        peajes = request.data.get('peajes', 0)
        total_pagar = request.data.get('total_pagar', 0)
        # inspector max_length=20 en la tabla — truncar por seguridad
        inspector = str(request.data.get('inspector', '') or '')[:20]

        if not fecha:
            return Response({'error': 'La fecha de inspección es requerida.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            km_val = float(km) if km not in (None, '', 'null') else 0
            costo_val = float(costo) if costo not in (None, '', 'null') else 0
            viaticos_val = float(viaticos) if viaticos not in (None, '', 'null') else 0
            peajes_val = float(peajes) if peajes not in (None, '', 'null') else 0
            total_pagar_val = float(total_pagar) if total_pagar not in (None, '', 'null') else 0
            inspeccion = Inspeccion.objects.create(
                id_siniestro=siniestro,
                fecha_inspeccion=fecha,
                km_recorridos=km_val,
                inspector=inspector,
                costo=costo_val,
                viaticos=viaticos_val,
                peajes=peajes_val,
                total_pagar=total_pagar_val,
            )
        except Exception as e:
            traceback.print_exc()
            return Response({'error': f'Error al guardar inspección: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'id': inspeccion.id_inspeccion,
            'fecha_inspeccion': str(inspeccion.fecha_inspeccion),
            'km_recorridos': float(inspeccion.km_recorridos or 0),
            'inspector': inspeccion.inspector or '',
            'costo': float(inspeccion.costo or 0),
            'viaticos': float(inspeccion.viaticos or 0),
            'peajes': float(inspeccion.peajes or 0),
            'total_pagar': float(inspeccion.total_pagar or 0),
        }, status=status.HTTP_201_CREATED)


class AdminSiniestrosPorAjustadorAPIView(APIView):
    """
    GET /api/admin/siniestros-por-ajustador/
    Devuelve todos los siniestros del sistema con info del ajustador asignado,
    más un resumen agregado por ajustador (total_siniestros, honorarios, por estado).
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        # Parámetros opcionales de filtro
        ajustador_filter = request.query_params.get('ajustador', None)
        estado_filter = request.query_params.get('estado', None)
        aseguradora_filter = request.query_params.get('aseguradora', None)

        siniestros_qs = Siniestro.objects.select_related('ajustador', 'aseguradora')

        if ajustador_filter:
            siniestros_qs = siniestros_qs.filter(ajustador__username__icontains=ajustador_filter)
        if estado_filter:
            siniestros_qs = siniestros_qs.filter(estado_conclusion=estado_filter)
        if aseguradora_filter:
            siniestros_qs = siniestros_qs.filter(aseguradora__nombre__icontains=aseguradora_filter)

        # Lista plana de siniestros
        siniestros_data = []
        resumen_por_ajustador = {}

        for s in siniestros_qs:
            ajustador_name = s.ajustador.username if s.ajustador else 'Sin asignar'
            honorario = float(s.honorario) if s.honorario else 0.0
            estado = s.estado_conclusion or 'PENDIENTE'

            siniestros_data.append({
                'id': s.id,
                'numero_siniestro': s.numero_siniestro or '',
                'folio': s.folio or '',
                'ajustador': ajustador_name,
                'ajustador_id': s.ajustador.id if s.ajustador else None,
                'aseguradora': s.aseguradora.nombre if s.aseguradora else '',
                'asegurado': s.asegurado or '',
                'poliza': s.poliza or '',
                'ramo': s.ramo or '',
                'gerente': s.gerente or '',
                'honorario': honorario,
                'estado_conclusion': estado,
                'fecha_asignacion': s.fecha_asignacion.strftime('%Y-%m-%d') if s.fecha_asignacion else None,
                'fecha_liquidacion': s.fecha_liquidacion.strftime('%Y-%m-%d') if s.fecha_liquidacion else None,
                'fecha_inspeccion': s.fecha_inspeccion.strftime('%Y-%m-%d') if s.fecha_inspeccion else None,
                'inspector': s.inspector or '',
                'kilometros': s.kilometros or 0,
                'dias': s.dias or 0,
                'rango': s.rango or '',
            })

            # Acumular resumen por ajustador
            if ajustador_name not in resumen_por_ajustador:
                resumen_por_ajustador[ajustador_name] = {
                    'ajustador': ajustador_name,
                    'ajustador_id': s.ajustador.id if s.ajustador else None,
                    'total_siniestros': 0,
                    'total_honorarios': 0.0,
                    'pendientes': 0,
                    'en_proceso': 0,
                    'concluidos': 0,
                }
            r = resumen_por_ajustador[ajustador_name]
            r['total_siniestros'] += 1
            r['total_honorarios'] += honorario
            estado_upper = estado.upper()
            if 'PENDIENTE' in estado_upper:
                r['pendientes'] += 1
            elif 'CONCLU' in estado_upper or 'PAGAD' in estado_upper or 'LIQUID' in estado_upper:
                r['concluidos'] += 1
            else:
                r['en_proceso'] += 1

        return Response({
            'siniestros': siniestros_data,
            'resumen_ajustadores': sorted(resumen_por_ajustador.values(), key=lambda x: x['total_siniestros'], reverse=True),
            'totales': {
                'total_siniestros': len(siniestros_data),
                'total_honorarios': sum(s['honorario'] for s in siniestros_data),
                'total_ajustadores': len(resumen_por_ajustador),
            }
        })


class MisInspeccionesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsInspectorRole]

    def get(self, request):
        try:
            inspector_custom = UsuarioCustom.objects.get(username=request.user.username)
        except UsuarioCustom.DoesNotExist:
            return Response({"warning": "El usuario no tiene perfil de inspector.", "inspecciones": [], "resumen": []})

        mes_filter = request.query_params.get("mes", None)
        inspecciones_qs = Inspeccion.objects.select_related(
            "id_siniestro", "id_siniestro__aseguradora", "id_siniestro__ajustador"
        ).filter(id_siniestro__ajustador=inspector_custom)

        if mes_filter:
            try:
                anio, mes = mes_filter.split("-")
                inspecciones_qs = inspecciones_qs.filter(
                    fecha_inspeccion__year=int(anio), fecha_inspeccion__month=int(mes)
                )
            except (ValueError, AttributeError):
                pass

        inspecciones_data = []
        total_general = 0.0
        from collections import defaultdict
        resumen_mes = defaultdict(lambda: {"total": 0.0, "count": 0})

        for i in inspecciones_qs:
            s = i.id_siniestro
            aseg = s.aseguradora
            total = float(i.total_pagar or 0)
            mes_key = i.fecha_inspeccion.strftime("%Y-%m") if i.fecha_inspeccion else "Sin fecha"
            inspecciones_data.append({
                "id": i.id_inspeccion,
                "numero_siniestro": s.numero_siniestro or "",
                "asegurado": s.asegurado or "",
                "aseguradora": aseg.nombre if aseg else "",
                "solo_inspecciones": aseg.solo_inspecciones if aseg else False,
                "fecha_inspeccion": i.fecha_inspeccion.strftime("%Y-%m-%d") if i.fecha_inspeccion else None,
                "km_recorridos": float(i.km_recorridos or 0),
                "costo": float(i.costo or 0),
                "viaticos": float(i.viaticos or 0),
                "peajes": float(i.peajes or 0),
                "total_pagar": total,
                "mes": mes_key,
            })
            total_general += total
            resumen_mes[mes_key]["total"] += total
            resumen_mes[mes_key]["count"] += 1

        resumen = [
            {"mes": m, "total": round(v["total"], 2), "num_inspecciones": v["count"]}
            for m, v in sorted(resumen_mes.items(), reverse=True)
        ]
        return Response({"inspecciones": inspecciones_data, "resumen": resumen, "total_general": round(total_general, 2)})


class InspectoresListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        inspectores = UsuarioCustom.objects.filter(rol="INSPECTOR").values_list("username", flat=True)
        return Response(list(inspectores))
