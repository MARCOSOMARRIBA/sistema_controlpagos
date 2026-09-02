from rest_framework import permissions
from .models import UsuarioCustom

def get_user_role(user):
    if not user or not user.is_authenticated:
        return None
    try:
        custom_user = UsuarioCustom.objects.get(username=user.username)
        return custom_user.rol
    except UsuarioCustom.DoesNotExist:
        return None

class IsAdminRole(permissions.BasePermission):
    """Permite acceso exclusivo a usuarios con rol ADMIN."""
    def has_permission(self, request, view):
        return get_user_role(request.user) == 'ADMIN'

class IsAjustadorRole(permissions.BasePermission):
    """Permite acceso exclusivo a usuarios con rol AJUSTADOR."""
    def has_permission(self, request, view):
        return get_user_role(request.user) == 'AJUSTADOR'

class IsAdminOrAjustadorOwner(permissions.BasePermission):
    """
    Control de acceso:
    - ADMIN: Tiene acceso a todo.
    - AJUSTADOR: Solo tiene acceso si el objeto le pertenece.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        rol = get_user_role(request.user)
        if rol == 'ADMIN':
            return True
        return hasattr(obj, 'ajustador') and obj.ajustador and obj.ajustador.username == request.user.username
