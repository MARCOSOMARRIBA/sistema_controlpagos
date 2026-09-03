from django.urls import path
from .views import (
    CargarSiniestroAPIView,
    AseguradorasListAPIView,
    ReporteAjustadoresAPIView,
    CorteMensualAPIView,
    LimpiarDatosAPIView,
    MisSiniestrosAPIView,
    MisGastosAPIView,
    CargarGridMasivoAPIView,
    CargarSiniestrosAjustadorAPIView,
    GerentesListAPIView,
    AjustadoresListAPIView,
    UsuariosListCreateAPIView,
    SiniestroInspeccionesAPIView,
    AdminSiniestrosPorAjustadorAPIView,
    MisInspeccionesAPIView,
    InspectoresListAPIView,
)

urlpatterns = [
    path('ajustador/cargar-siniestro/', CargarSiniestroAPIView.as_view(), name='cargar-siniestro'),
    path('aseguradoras/', AseguradorasListAPIView.as_view(), name='listar-aseguradoras'),
    path('gerentes/', GerentesListAPIView.as_view(), name='listar-gerentes'),
    path('ajustadores/', AjustadoresListAPIView.as_view(), name='listar-ajustadores'),
    path('inspectores/', InspectoresListAPIView.as_view(), name='listar-inspectores'),
    path('reporte-ajustadores/', ReporteAjustadoresAPIView.as_view(), name='reporte-ajustadores'),
    path('usuarios/', UsuariosListCreateAPIView.as_view(), name='gestion-usuarios'),
    path('corte-mensual/', CorteMensualAPIView.as_view(), name='corte-mensual'),
    path('limpiar-datos/', LimpiarDatosAPIView.as_view(), name='limpiar-datos'),
    path('mis-siniestros/', MisSiniestrosAPIView.as_view(), name='mis-siniestros'),
    path('mis-gastos/', MisGastosAPIView.as_view(), name='mis-gastos'),
    path('mis-inspecciones/', MisInspeccionesAPIView.as_view(), name='mis-inspecciones'),
    path('cargar-grid-masivo/', CargarGridMasivoAPIView.as_view(), name='cargar-grid-masivo'),
    # FIX-003: Nuevo endpoint exclusivo para Ajustador — fuerza id_ajustador autenticado
    path('ajustador/cargar-siniestros/', CargarSiniestrosAjustadorAPIView.as_view(), name='ajustador-cargar-siniestros'),
    path('siniestros/<int:siniestro_id>/inspecciones/', SiniestroInspeccionesAPIView.as_view(), name='siniestro-inspecciones'),
    path('admin/siniestros-por-ajustador/', AdminSiniestrosPorAjustadorAPIView.as_view(), name='admin-siniestros-por-ajustador'),
]
