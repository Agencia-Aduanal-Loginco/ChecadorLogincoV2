"""
Permisos personalizados para la app it_tickets.

EsGrupoIT:
  Permite acceso solo a usuarios que pertenecen al grupo 'IT'.
  Se usa para la gestión de tickets, inventario y mantenimientos.

EsPropietarioTicketOIT:
  Permite lectura al empleado dueño del ticket.
  Permite escritura (cambio de estado, actualización) solo al grupo IT.
"""
from rest_framework.permissions import BasePermission

GRUPO_IT = 'IT'


def usuario_es_it(user):
    """Función helper reutilizable para verificar membresía en el grupo IT."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=GRUPO_IT).exists()


class EsGrupoIT(BasePermission):
    """
    Permite acceso solo a miembros del grupo IT (o superusuarios).
    Aplicar a ViewSets de inventario, mantenimientos y gestión avanzada de tickets.
    """
    message = "Solo el equipo de IT puede realizar esta acción."

    def has_permission(self, request, view):
        return usuario_es_it(request.user)


class EsGrupoITOLectura(BasePermission):
    """
    Permite lectura a cualquier usuario autenticado.
    Solo IT puede crear, modificar o eliminar.
    """
    message = "Solo el equipo de IT puede modificar estos recursos."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Métodos de solo lectura permitidos a todos los autenticados
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return usuario_es_it(request.user)


class EsPropietarioTicketOIT(BasePermission):
    """
    Permiso a nivel de objeto.
    - GET: el empleado dueño del ticket O un miembro de IT.
    - PUT/PATCH/DELETE: solo IT.
    """
    message = "No tienes permiso para acceder a este ticket."

    def has_object_permission(self, request, view, obj):
        if usuario_es_it(request.user):
            return True

        # El empleado puede ver su propio ticket
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            try:
                return obj.empleado.user == request.user
            except AttributeError:
                return False

        return False
