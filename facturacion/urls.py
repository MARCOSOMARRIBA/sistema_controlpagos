from django.urls import path
from .views import (
    FacturasListAPIView,
    FacturaDetailAPIView,
    AutorizarFacturaAPIView,
    RechazarFacturaAPIView,
    SiniestrosParaFacturaAPIView,
    FacturaStatsAPIView,
    FacturaGuardarAPIView,
)

urlpatterns = [
    path('facturas/', FacturasListAPIView.as_view(), name='facturas-list'),
    path('guardar/', FacturaGuardarAPIView.as_view(), name='factura-guardar'),
    path('facturas/<int:pk>/', FacturaDetailAPIView.as_view(), name='factura-detail'),
    path('facturas/<int:pk>/autorizar/', AutorizarFacturaAPIView.as_view(), name='factura-autorizar'),
    path('facturas/<int:pk>/rechazar/', RechazarFacturaAPIView.as_view(), name='factura-rechazar'),
    path('siniestros-disponibles/', SiniestrosParaFacturaAPIView.as_view(), name='siniestros-disponibles'),
    path('stats/', FacturaStatsAPIView.as_view(), name='facturacion-stats'),
]
