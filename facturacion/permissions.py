"""
Permisos del módulo de facturación.

Incluye permisos especializados para el flujo de solicitud/autorización.
"""
from rest_framework import permissions
from siniestros.permissions import IsAdminRole, IsAjustadorRole, get_user_role  # noqa: F401


class CanRequestFactura(permissions.BasePermission):
    """
    Permite a cualquier usuario autenticado (AJUSTADOR o ADMIN) solicitar una factura.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class CanAuthorizeFactura(permissions.BasePermission):
    """
    Solo ADMIN puede autorizar o rechazar facturas.
    """
    def has_permission(self, request, view):
        return get_user_role(request.user) == 'ADMIN'


class IsFacturaOwnerOrAdmin(permissions.BasePermission):
    """
    Un ajustador solo puede ver/editar sus propias facturas.
    Un admin puede ver/editar todas.
    """
    def has_object_permission(self, request, view, obj):
        role = get_user_role(request.user)
        if role == 'ADMIN':
            return True
        return (
            hasattr(obj, 'id_ajustador') and
            obj.id_ajustador and
            obj.id_ajustador.username == request.user.username
        )
