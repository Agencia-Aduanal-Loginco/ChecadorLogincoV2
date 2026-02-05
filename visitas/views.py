from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import MotivoVisita, Visita
from .serializers import (
    MotivoVisitaSerializer,
    VisitaListSerializer,
    VisitaDetailSerializer,
    VisitaCreateSerializer,
    VisitaUpdateSerializer,
    AutorizarVisitaSerializer,
    VerificarQRSerializer,
    RegistrarMovimientoSerializer,
)
from organizacion.models import Departamento
from empleados.models import Empleado


class MotivoVisitaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de motivos de visita.
    """
    queryset = MotivoVisita.objects.all()
    serializer_class = MotivoVisitaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)

        return queryset


class VisitaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de visitas.
    """
    queryset = Visita.objects.all().select_related(
        'departamento_destino', 'autorizado_por'
    )

    def get_permissions(self):
        if self.action in ['create', 'verificar_qr', 'registrar_movimiento']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'list':
            return VisitaListSerializer
        elif self.action == 'create':
            return VisitaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VisitaUpdateSerializer
        elif self.action in ['autorizar', 'rechazar']:
            return AutorizarVisitaSerializer
        elif self.action == 'verificar_qr':
            return VerificarQRSerializer
        elif self.action == 'registrar_movimiento':
            return RegistrarMovimientoSerializer
        return VisitaDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filtrar por estado
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)

        # Filtrar por fecha
        fecha = self.request.query_params.get('fecha', None)
        if fecha:
            queryset = queryset.filter(fecha_programada=fecha)

        # Filtrar visitas de hoy
        hoy = self.request.query_params.get('hoy', None)
        if hoy and hoy.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(fecha_programada=timezone.now().date())

        # Filtrar por departamento
        departamento = self.request.query_params.get('departamento', None)
        if departamento:
            queryset = queryset.filter(departamento_destino_id=departamento)


        # Buscar
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(nombre_visitante__icontains=search) |
                models.Q(empresa__icontains=search) |
                models.Q(email__icontains=search)
            )

        return queryset

    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        """Autorizar visita"""
        visita = self.get_object()

        if visita.estado != 'pendiente':
            return Response(
                {'error': 'Solo se pueden autorizar visitas pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(request.user, 'empleado'):
            return Response(
                {'error': 'No tienes un perfil de empleado asociado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AutorizarVisitaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visita.autorizar(request.user.empleado, serializer.validated_data.get('comentarios', ''))
        return Response(VisitaDetailSerializer(visita).data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """Rechazar visita"""
        visita = self.get_object()

        if visita.estado != 'pendiente':
            return Response(
                {'error': 'Solo se pueden rechazar visitas pendientes.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(request.user, 'empleado'):
            return Response(
                {'error': 'No tienes un perfil de empleado asociado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AutorizarVisitaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visita.rechazar(request.user.empleado, serializer.validated_data.get('comentarios', ''))
        return Response(VisitaDetailSerializer(visita).data)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verificar_qr(self, request):
        """Verificar codigo QR de visita"""
        serializer = VerificarQRSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        codigo = serializer.validated_data['codigo']
        try:
            visita = Visita.objects.get(codigo_visita=codigo)
            return Response({
                'encontrada': True,
                'visita': VisitaDetailSerializer(visita).data
            })
        except Visita.DoesNotExist:
            return Response({
                'encontrada': False,
                'error': 'Visita no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def registrar_movimiento(self, request):
        """Registrar entrada o salida de visitante"""
        serializer = RegistrarMovimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        codigo = serializer.validated_data['codigo']
        tipo = serializer.validated_data['tipo']

        try:
            visita = Visita.objects.get(codigo_visita=codigo)

            if tipo == 'entrada':
                if not visita.puede_registrar_entrada():
                    return Response({
                        'success': False,
                        'error': 'No se puede registrar entrada. Estado actual: ' + visita.get_estado_display()
                    }, status=status.HTTP_400_BAD_REQUEST)
                visita.registrar_entrada()
                return Response({
                    'success': True,
                    'message': 'Entrada registrada exitosamente',
                    'visita': VisitaDetailSerializer(visita).data
                })

            elif tipo == 'salida':
                if not visita.puede_registrar_salida():
                    return Response({
                        'success': False,
                        'error': 'No se puede registrar salida. Estado actual: ' + visita.get_estado_display()
                    }, status=status.HTTP_400_BAD_REQUEST)
                visita.registrar_salida()
                return Response({
                    'success': True,
                    'message': 'Salida registrada exitosamente',
                    'visita': VisitaDetailSerializer(visita).data
                })

        except Visita.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Visita no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)


# ===== VISTAS WEB =====

def registrar_visita_view(request):
    """Vista publica para registrar una visita"""
    departamentos = Departamento.objects.filter(activo=True)

    if request.method == 'POST':
        try:
            visita = Visita.objects.create(
                nombre_visitante=request.POST.get('nombre_visitante'),
                empresa=request.POST.get('empresa', ''),
                email=request.POST.get('email', ''),
                telefono=request.POST.get('telefono', ''),
                identificacion_tipo=request.POST.get('identificacion_tipo', 'ine'),
                identificacion_numero=request.POST.get('identificacion_numero', ''),
                foto_visitante=request.FILES.get('foto_visitante'),
                foto_identificacion=request.FILES.get('foto_identificacion'),
                motivo=request.POST.get('motivo'),
                departamento_destino_id=request.POST.get('departamento_destino') or None,
                fecha_programada=request.POST.get('fecha_programada'),
                hora_programada=request.POST.get('hora_programada'),
                duracion_estimada=int(request.POST.get('duracion_estimada', 60)),
                estado='autorizado'  # Autorizacion automatica
            )

            # Generar QR automaticamente
            visita.generar_qr()
            visita.save()

            return render(request, 'visitas/registro_exitoso.html', {
                'visita': visita
            })

        except Exception as e:
            messages.error(request, f'Error al registrar la visita: {str(e)}')

    return render(request, 'visitas/registrar_visita.html', {
        'departamentos': departamentos
    })


def verificar_qr_view(request):
    """Vista para escanear y verificar codigos QR"""
    return render(request, 'visitas/verificar_qr.html')


def verificar_resultado_view(request, codigo):
    """Vista para mostrar resultado de verificacion"""
    try:
        visita = Visita.objects.get(codigo_visita=codigo)
        return render(request, 'visitas/verificar_resultado.html', {
            'visita': visita,
            'encontrada': True
        })
    except Visita.DoesNotExist:
        return render(request, 'visitas/verificar_resultado.html', {
            'encontrada': False,
            'codigo': codigo
        })


@login_required
def lista_visitas_view(request):
    """Vista para listar visitas (staff)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta pagina.')
        return redirect('dashboard')

    fecha = request.GET.get('fecha', timezone.now().date())
    estado = request.GET.get('estado', '')

    visitas = Visita.objects.select_related(
        'departamento_destino'
    ).order_by('-fecha_programada', '-hora_programada')

    if fecha:
        visitas = visitas.filter(fecha_programada=fecha)

    if estado:
        visitas = visitas.filter(estado=estado)

    # Estadisticas del dia
    hoy = timezone.now().date()
    stats = {
        'hoy_total': Visita.objects.filter(fecha_programada=hoy).count(),
        'hoy_pendientes': Visita.objects.filter(fecha_programada=hoy, estado='pendiente').count(),
        'hoy_en_sitio': Visita.objects.filter(fecha_programada=hoy, estado='en_sitio').count(),
        'hoy_finalizadas': Visita.objects.filter(fecha_programada=hoy, estado='finalizado').count(),
    }

    return render(request, 'visitas/lista_visitas.html', {
        'visitas': visitas,
        'stats': stats,
        'fecha_filtro': fecha,
        'estado_filtro': estado
    })


@login_required
def detalle_visita_view(request, pk):
    """Vista para ver detalle de visita"""
    visita = get_object_or_404(Visita, pk=pk)

    return render(request, 'visitas/detalle_visita.html', {
        'visita': visita
    })


@login_required
@require_POST
def accion_visita_view(request, pk, accion):
    """Vista para ejecutar acciones sobre visitas"""
    visita = get_object_or_404(Visita, pk=pk)

    if not hasattr(request.user, 'empleado'):
        return JsonResponse({'success': False, 'message': 'No tienes un perfil de empleado asociado.'})

    empleado = request.user.empleado
    comentarios = request.POST.get('comentarios', '')

    try:
        if accion == 'autorizar':
            if visita.estado != 'pendiente':
                return JsonResponse({'success': False, 'message': 'Solo se pueden autorizar visitas pendientes.'})
            visita.autorizar(empleado, comentarios)
            return JsonResponse({'success': True, 'message': 'Visita autorizada. Se ha generado el codigo QR.'})

        elif accion == 'rechazar':
            if visita.estado != 'pendiente':
                return JsonResponse({'success': False, 'message': 'Solo se pueden rechazar visitas pendientes.'})
            visita.rechazar(empleado, comentarios)
            return JsonResponse({'success': True, 'message': 'Visita rechazada.'})

        elif accion == 'entrada':
            if not visita.puede_registrar_entrada():
                return JsonResponse({'success': False, 'message': 'No se puede registrar entrada.'})
            visita.registrar_entrada()
            return JsonResponse({'success': True, 'message': 'Entrada registrada.'})

        elif accion == 'salida':
            if not visita.puede_registrar_salida():
                return JsonResponse({'success': False, 'message': 'No se puede registrar salida.'})
            visita.registrar_salida()
            return JsonResponse({'success': True, 'message': 'Salida registrada.'})

        elif accion == 'cancelar':
            if visita.estado not in ['pendiente', 'autorizado']:
                return JsonResponse({'success': False, 'message': 'No se puede cancelar esta visita.'})
            visita.cancelar()
            return JsonResponse({'success': True, 'message': 'Visita cancelada.'})

        else:
            return JsonResponse({'success': False, 'message': 'Accion no valida.'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def api_verificar_qr(request):
    """API para verificar QR desde el escaner"""
    codigo = request.POST.get('codigo', '')

    if not codigo:
        return JsonResponse({'success': False, 'error': 'Codigo no proporcionado'})

    try:
        visita = Visita.objects.get(codigo_visita=codigo)
        return JsonResponse({
            'success': True,
            'visita': {
                'id': visita.id,
                'codigo_corto': visita.codigo_corto,
                'nombre_visitante': visita.nombre_visitante,
                'empresa': visita.empresa,
                'motivo': visita.motivo.nombre,
                'fecha_programada': visita.fecha_programada.strftime('%Y-%m-%d'),
                'hora_programada': visita.hora_programada.strftime('%H:%M'),
                'estado': visita.estado,
                'estado_display': visita.get_estado_display(),
                'puede_entrada': visita.puede_registrar_entrada(),
                'puede_salida': visita.puede_registrar_salida(),
            }
        })
    except Visita.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Visita no encontrada'})


@require_POST
def api_registrar_movimiento(request):
    """API para registrar entrada/salida desde el escaner"""
    codigo = request.POST.get('codigo', '')
    tipo = request.POST.get('tipo', '')

    if not codigo or not tipo:
        return JsonResponse({'success': False, 'error': 'Datos incompletos'})

    try:
        visita = Visita.objects.get(codigo_visita=codigo)

        if tipo == 'entrada':
            if not visita.puede_registrar_entrada():
                return JsonResponse({
                    'success': False,
                    'error': f'No se puede registrar entrada. Estado: {visita.get_estado_display()}'
                })
            visita.registrar_entrada()
            return JsonResponse({'success': True, 'message': 'Entrada registrada'})

        elif tipo == 'salida':
            if not visita.puede_registrar_salida():
                return JsonResponse({
                    'success': False,
                    'error': f'No se puede registrar salida. Estado: {visita.get_estado_display()}'
                })
            visita.registrar_salida()
            return JsonResponse({'success': True, 'message': 'Salida registrada'})

        else:
            return JsonResponse({'success': False, 'error': 'Tipo de movimiento no valido'})

    except Visita.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Visita no encontrada'})
