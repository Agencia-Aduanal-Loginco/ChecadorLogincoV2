from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import TipoPermiso, SolicitudPermiso, HistorialPermiso
from .serializers import (
    TipoPermisoSerializer,
    SolicitudPermisoListSerializer,
    SolicitudPermisoDetailSerializer,
    SolicitudPermisoCreateSerializer,
    SolicitudPermisoUpdateSerializer,
    AprobarRechazarSerializer,
)


class TipoPermisoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de tipos de permiso.
    """
    queryset = TipoPermiso.objects.all()
    serializer_class = TipoPermisoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtrar por activo
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)

        return queryset


class SolicitudPermisoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de solicitudes de permiso.
    """
    queryset = SolicitudPermiso.objects.all().select_related(
        'empleado', 'empleado__user', 'tipo_permiso', 'aprobador'
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return SolicitudPermisoListSerializer
        elif self.action == 'create':
            return SolicitudPermisoCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SolicitudPermisoUpdateSerializer
        elif self.action in ['aprobar', 'rechazar']:
            return AprobarRechazarSerializer
        return SolicitudPermisoDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Si no es staff, solo ve sus propias solicitudes
        if not user.is_staff:
            if hasattr(user, 'empleado'):
                queryset = queryset.filter(empleado=user.empleado)
            else:
                return queryset.none()

        # Filtrar por estado
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)

        # Filtrar por empleado
        empleado = self.request.query_params.get('empleado', None)
        if empleado:
            queryset = queryset.filter(empleado_id=empleado)

        # Filtrar por tipo
        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo_permiso_id=tipo)

        # Filtrar por fecha
        fecha_desde = self.request.query_params.get('fecha_desde', None)
        if fecha_desde:
            queryset = queryset.filter(fecha_inicio__gte=fecha_desde)

        fecha_hasta = self.request.query_params.get('fecha_hasta', None)
        if fecha_hasta:
            queryset = queryset.filter(fecha_fin__lte=fecha_hasta)

        # Filtrar pendientes de aprobar (para supervisores)
        pendientes = self.request.query_params.get('pendientes_aprobar', None)
        if pendientes and pendientes.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(estado='pendiente')

        return queryset

    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        """Enviar solicitud para aprobacion"""
        solicitud = self.get_object()

        if solicitud.estado != 'borrador':
            return Response(
                {'error': 'Solo se pueden enviar solicitudes en estado borrador.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        solicitud.enviar()
        return Response(SolicitudPermisoDetailSerializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprobar solicitud"""
        solicitud = self.get_object()

        if solicitud.estado != 'pendiente':
            return Response(
                {'error': 'Solo se pueden aprobar solicitudes pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(request.user, 'empleado'):
            return Response(
                {'error': 'No tienes un perfil de empleado asociado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aprobador = request.user.empleado
        if not solicitud.puede_ser_aprobado_por(aprobador):
            return Response(
                {'error': 'No tienes permisos para aprobar esta solicitud.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AprobarRechazarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        solicitud.aprobar(aprobador, serializer.validated_data.get('comentarios', ''))
        return Response(SolicitudPermisoDetailSerializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """Rechazar solicitud"""
        solicitud = self.get_object()

        if solicitud.estado != 'pendiente':
            return Response(
                {'error': 'Solo se pueden rechazar solicitudes pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(request.user, 'empleado'):
            return Response(
                {'error': 'No tienes un perfil de empleado asociado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        aprobador = request.user.empleado
        if not solicitud.puede_ser_aprobado_por(aprobador):
            return Response(
                {'error': 'No tienes permisos para rechazar esta solicitud.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AprobarRechazarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        solicitud.rechazar(aprobador, serializer.validated_data.get('comentarios', ''))
        return Response(SolicitudPermisoDetailSerializer(solicitud).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar solicitud"""
        solicitud = self.get_object()

        if solicitud.estado not in ['borrador', 'pendiente']:
            return Response(
                {'error': 'Solo se pueden cancelar solicitudes en borrador o pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(request.user, 'empleado'):
            return Response(
                {'error': 'No tienes un perfil de empleado asociado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Solo el solicitante o staff pueden cancelar
        if request.user.empleado != solicitud.empleado and not request.user.is_staff:
            return Response(
                {'error': 'No tienes permisos para cancelar esta solicitud.'},
                status=status.HTTP_403_FORBIDDEN
            )

        solicitud.cancelar(request.user.empleado, 'Cancelado por el usuario')
        return Response(SolicitudPermisoDetailSerializer(solicitud).data)


# ===== VISTAS WEB =====

@login_required
def mis_permisos_view(request):
    """Vista para ver los permisos del empleado"""
    if not hasattr(request.user, 'empleado'):
        messages.error(request, 'No tienes un perfil de empleado asociado.')
        return redirect('dashboard')

    empleado = request.user.empleado
    solicitudes = SolicitudPermiso.objects.filter(
        empleado=empleado
    ).select_related('tipo_permiso').order_by('-fecha_creacion')

    # Estadisticas
    stats = {
        'total': solicitudes.count(),
        'pendientes': solicitudes.filter(estado='pendiente').count(),
        'aprobados': solicitudes.filter(estado='aprobado').count(),
        'rechazados': solicitudes.filter(estado='rechazado').count(),
    }

    return render(request, 'permisos/mis_permisos.html', {
        'solicitudes': solicitudes,
        'stats': stats
    })


@login_required
def nueva_solicitud_view(request):
    """Vista para crear una nueva solicitud de permiso"""
    if not hasattr(request.user, 'empleado'):
        messages.error(request, 'No tienes un perfil de empleado asociado.')
        return redirect('dashboard')

    tipos_permiso = TipoPermiso.objects.filter(activo=True)

    if request.method == 'POST':
        empleado = request.user.empleado
        tipo_permiso_id = request.POST.get('tipo_permiso')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')
        hora_inicio = request.POST.get('hora_inicio') or None
        hora_fin = request.POST.get('hora_fin') or None
        motivo = request.POST.get('motivo')
        evidencia = request.FILES.get('evidencia')
        accion = request.POST.get('accion', 'borrador')

        try:
            tipo_permiso = TipoPermiso.objects.get(id=tipo_permiso_id)

            solicitud = SolicitudPermiso.objects.create(
                empleado=empleado,
                tipo_permiso=tipo_permiso,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                motivo=motivo,
                evidencia=evidencia,
                estado='borrador'
            )

            HistorialPermiso.objects.create(
                solicitud=solicitud,
                accion='creado',
                usuario=empleado,
                comentarios='Solicitud creada'
            )

            if accion == 'enviar':
                solicitud.enviar()
                messages.success(request, 'Solicitud enviada para aprobacion.')
            else:
                messages.success(request, 'Solicitud guardada como borrador.')

            return redirect('mis_permisos')

        except TipoPermiso.DoesNotExist:
            messages.error(request, 'Tipo de permiso no valido.')
        except Exception as e:
            messages.error(request, f'Error al crear la solicitud: {str(e)}')

    return render(request, 'permisos/nueva_solicitud.html', {
        'tipos_permiso': tipos_permiso
    })


@login_required
def detalle_permiso_view(request, pk):
    """Vista para ver el detalle de una solicitud"""
    solicitud = get_object_or_404(SolicitudPermiso, pk=pk)

    # Verificar permisos
    if not request.user.is_staff:
        if not hasattr(request.user, 'empleado') or request.user.empleado != solicitud.empleado:
            messages.error(request, 'No tienes permisos para ver esta solicitud.')
            return redirect('mis_permisos')

    historial = solicitud.historial.all().order_by('-fecha')

    return render(request, 'permisos/detalle_permiso.html', {
        'solicitud': solicitud,
        'historial': historial
    })


@login_required
def aprobar_permisos_view(request):
    """Vista para aprobar permisos (staff)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta pagina.')
        return redirect('dashboard')

    solicitudes = SolicitudPermiso.objects.filter(
        estado='pendiente'
    ).select_related('empleado', 'empleado__user', 'tipo_permiso').order_by('-fecha_creacion')

    return render(request, 'permisos/aprobar_permisos.html', {
        'solicitudes': solicitudes
    })


@login_required
@require_POST
def accion_permiso_view(request, pk, accion):
    """Vista para ejecutar acciones sobre permisos"""
    solicitud = get_object_or_404(SolicitudPermiso, pk=pk)

    if not hasattr(request.user, 'empleado'):
        return JsonResponse({'success': False, 'message': 'No tienes un perfil de empleado asociado.'})

    empleado = request.user.empleado
    comentarios = request.POST.get('comentarios', '')

    try:
        if accion == 'enviar':
            if solicitud.estado != 'borrador':
                return JsonResponse({'success': False, 'message': 'Solo se pueden enviar solicitudes en borrador.'})
            if empleado != solicitud.empleado:
                return JsonResponse({'success': False, 'message': 'No tienes permisos para enviar esta solicitud.'})
            solicitud.enviar()
            return JsonResponse({'success': True, 'message': 'Solicitud enviada para aprobacion.'})

        elif accion == 'aprobar':
            if solicitud.estado != 'pendiente':
                return JsonResponse({'success': False, 'message': 'Solo se pueden aprobar solicitudes pendientes.'})
            if not solicitud.puede_ser_aprobado_por(empleado):
                return JsonResponse({'success': False, 'message': 'No tienes permisos para aprobar esta solicitud.'})
            solicitud.aprobar(empleado, comentarios)
            return JsonResponse({'success': True, 'message': 'Solicitud aprobada.'})

        elif accion == 'rechazar':
            if solicitud.estado != 'pendiente':
                return JsonResponse({'success': False, 'message': 'Solo se pueden rechazar solicitudes pendientes.'})
            if not solicitud.puede_ser_aprobado_por(empleado):
                return JsonResponse({'success': False, 'message': 'No tienes permisos para rechazar esta solicitud.'})
            solicitud.rechazar(empleado, comentarios)
            return JsonResponse({'success': True, 'message': 'Solicitud rechazada.'})

        elif accion == 'cancelar':
            if solicitud.estado not in ['borrador', 'pendiente']:
                return JsonResponse({'success': False, 'message': 'Solo se pueden cancelar solicitudes en borrador o pendientes.'})
            if empleado != solicitud.empleado and not request.user.is_staff:
                return JsonResponse({'success': False, 'message': 'No tienes permisos para cancelar esta solicitud.'})
            solicitud.cancelar(empleado, comentarios)
            return JsonResponse({'success': True, 'message': 'Solicitud cancelada.'})

        else:
            return JsonResponse({'success': False, 'message': 'Accion no valida.'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
