"""
Vistas de la app it_tickets.

API REST (DRF ViewSets):
  EquipoComputoViewSet   -> CRUD inventario (solo IT)
  TicketViewSet          -> CRUD tickets + endpoint de cambio de estado
  MantenimientoViewSet   -> CRUD mantenimientos (solo IT)

Vistas web (función-based, requieren login de sesión):
  dashboard_it_view      -> Métricas y listado rápido
  lista_tickets_view     -> Listado con filtros
  detalle_ticket_view    -> Detalle + historial
  inventario_view        -> Gestión de inventario
  calendario_mantenimiento_view -> Vista de calendario
"""
import csv
import io
import logging
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Count, Q, Avg
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from empleados.models import Empleado
from .models import (
    EquipoComputo, Ticket, HistorialTicket, MantenimientoEquipo,
    EstadoTicket, EstadoEquipo, TipoEquipo,
)
from .permissions import EsGrupoIT, EsGrupoITOLectura, EsPropietarioTicketOIT, usuario_es_it
from .serializers import (
    EquipoComputoSerializer, EquipoComputoResumenSerializer,
    TicketCrearSerializer, TicketListSerializer, TicketDetalleSerializer,
    TicketActualizarITSerializer, CambioEstadoSerializer,
    HistorialTicketSerializer, MantenimientoEquipoSerializer,
    ImportarCSVSerializer,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# API: EquipoComputo
# ===========================================================================

class EquipoComputoViewSet(viewsets.ModelViewSet):
    """
    CRUD de inventario de equipo de cómputo.
    Solo accesible para el grupo IT.

    list   GET    /api/it/equipos/
    create POST   /api/it/equipos/
    retrieve GET  /api/it/equipos/{id}/
    update  PUT   /api/it/equipos/{id}/
    partial_update PATCH /api/it/equipos/{id}/
    destroy DELETE /api/it/equipos/{id}/
    importar_csv POST /api/it/equipos/importar_csv/
    """

    queryset = EquipoComputo.objects.select_related('empleado__user').all()
    permission_classes = [IsAuthenticated, EsGrupoIT]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'numero_serie', 'marca', 'modelo',
        'usuario_nombre', 'empleado__user__first_name',
        'empleado__user__last_name', 'empleado__codigo_empleado',
    ]
    ordering_fields = ['marca', 'modelo', 'estado', 'fecha_proximo_mantenimiento']
    ordering = ['marca', 'modelo']

    def get_serializer_class(self):
        if self.action == 'list':
            return EquipoComputoSerializer
        return EquipoComputoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get('estado')
        tipo = self.request.query_params.get('tipo')
        mantenimiento_vencido = self.request.query_params.get('mantenimiento_vencido')

        if estado:
            qs = qs.filter(estado=estado)
        if tipo:
            qs = qs.filter(tipo=tipo)
        if mantenimiento_vencido == '1':
            qs = qs.filter(fecha_proximo_mantenimiento__lt=timezone.now().date())

        return qs

    @action(detail=False, methods=['post'], url_path='importar-csv')
    def importar_csv(self, request):
        """
        Importa el inventario desde un CSV con el formato del proyecto.

        Columnas esperadas (en orden):
        Codigo Empleado, Usuario, Tipo, Numero Serie, Marca, Modelo,
        R, U, Monitores, Marca(monitor), TELEFONO, TEF MAC

        Retorna estadísticas de la importación.
        """
        serializer = ImportarCSVSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        archivo = serializer.validated_data['archivo']
        actualizar_existentes = serializer.validated_data['actualizar_existentes']

        resultado = _procesar_csv_inventario(archivo, actualizar_existentes)
        return Response(resultado, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        """Métricas rápidas del inventario para el dashboard."""
        hoy = timezone.now().date()
        data = {
            'total': EquipoComputo.objects.count(),
            'activos': EquipoComputo.objects.filter(estado=EstadoEquipo.ACTIVO).count(),
            'en_mantenimiento': EquipoComputo.objects.filter(
                estado=EstadoEquipo.MANTENIMIENTO
            ).count(),
            'de_baja': EquipoComputo.objects.filter(estado=EstadoEquipo.BAJA).count(),
            'mantenimiento_vencido': EquipoComputo.objects.filter(
                fecha_proximo_mantenimiento__lt=hoy
            ).count(),
            'mantenimiento_proximo_7_dias': EquipoComputo.objects.filter(
                fecha_proximo_mantenimiento__gte=hoy,
                fecha_proximo_mantenimiento__lte=hoy + timedelta(days=7)
            ).count(),
        }
        return Response(data)


def _procesar_csv_inventario(archivo, actualizar_existentes=False):
    """
    Procesa el CSV del inventario y crea/actualiza registros en la BD.

    Mapeo de columnas del CSV original:
    [0] Codigo Empleado  -> empleado (FK por codigo_empleado)
    [1] Usuario          -> usuario_nombre
    [2] Tipo             -> tipo
    [3] Numero Serie     -> numero_serie
    [4] Marca            -> marca
    [5] Modelo           -> modelo
    [6] R                -> (ignorado, columna interna)
    [7] U                -> tiene_monitor (presencia de 'x')
    [8] Monitores        -> (número - guardado en notas si > 1)
    [9] Marca (monitor)  -> marca_monitor
    [10] TELEFONO        -> telefono_serie
    [11] TEF MAC         -> mac_telefono
    """
    creados = 0
    actualizados = 0
    omitidos = 0
    errores = []

    try:
        contenido = archivo.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        contenido = archivo.read().decode('latin-1')

    reader = csv.reader(io.StringIO(contenido))
    encabezado = next(reader, None)  # Saltar la fila de encabezado

    for num_fila, fila in enumerate(reader, start=2):
        # Normalizar fila para que siempre tenga 12 columnas
        while len(fila) < 12:
            fila.append('')

        codigo_empleado = fila[0].strip()
        usuario_nombre  = fila[1].strip()
        tipo_raw        = fila[2].strip().lower()
        numero_serie    = fila[3].strip().upper()
        marca           = fila[4].strip()
        modelo          = fila[5].strip()
        col_r           = fila[6].strip().lower()   # 'x' = tiene monitor externo (R)
        col_u           = fila[7].strip().lower()   # 'x' = tiene monitor USB
        monitores_raw   = fila[8].strip()
        marca_monitor   = fila[9].strip()
        telefono_serie  = fila[10].strip()
        mac_telefono    = fila[11].strip()

        if not numero_serie:
            errores.append(f"Fila {num_fila}: Número de serie vacío. Omitida.")
            omitidos += 1
            continue

        # Mapear tipo
        tipo_map = {
            'desktop': TipoEquipo.DESKTOP,
            'laptop': TipoEquipo.LAPTOP,
            'servidor': TipoEquipo.SERVIDOR,
            'impresora': TipoEquipo.IMPRESORA,
            'tablet': TipoEquipo.TABLET,
        }
        tipo = tipo_map.get(tipo_raw, TipoEquipo.DESKTOP)

        # Tiene monitor si cualquiera de las columnas R o U tiene 'x'
        tiene_monitor = bool(col_r == 'x' or col_u == 'x')

        # Buscar empleado por código
        empleado = None
        if codigo_empleado:
            try:
                empleado = Empleado.objects.get(codigo_empleado=codigo_empleado)
            except Empleado.DoesNotExist:
                # No bloqueamos la importación; guardamos el nombre en usuario_nombre
                pass

        # Notas adicionales
        notas = ''
        if monitores_raw and monitores_raw not in ('', ' ', 'x'):
            notas = f"Monitores: {monitores_raw}"
        if col_r == 'x' and col_u == 'x':
            notas += ' (monitor externo + USB)' if notas else '(monitor externo + USB)'

        datos = {
            'empleado': empleado,
            'usuario_nombre': usuario_nombre or codigo_empleado or 'Sin asignar',
            'tipo': tipo,
            'marca': marca,
            'modelo': modelo,
            'tiene_monitor': tiene_monitor,
            'marca_monitor': marca_monitor,
            'telefono_serie': telefono_serie,
            'mac_telefono': mac_telefono,
            'notas': notas,
        }

        try:
            with transaction.atomic():
                equipo_qs = EquipoComputo.objects.filter(numero_serie=numero_serie)
                if equipo_qs.exists():
                    if actualizar_existentes:
                        equipo_qs.update(**datos)
                        actualizados += 1
                    else:
                        omitidos += 1
                else:
                    EquipoComputo.objects.create(numero_serie=numero_serie, **datos)
                    creados += 1
        except Exception as e:
            errores.append(f"Fila {num_fila} (serie {numero_serie}): {str(e)}")
            omitidos += 1

    return {
        'creados': creados,
        'actualizados': actualizados,
        'omitidos': omitidos,
        'errores': errores,
        'total_procesado': creados + actualizados + omitidos,
    }


# ===========================================================================
# API: Ticket
# ===========================================================================

class TicketViewSet(viewsets.ModelViewSet):
    """
    CRUD de tickets + acciones especiales.

    Empleados:
      - Pueden crear tickets (POST /api/it/tickets/)
      - Pueden ver sus propios tickets (GET /api/it/tickets/?mis_tickets=1)

    IT:
      - Ve todos los tickets
      - Puede cambiar estado, prioridad, asignación, solución

    Acciones adicionales:
      cambiar_estado  POST /api/it/tickets/{id}/cambiar-estado/
      mis_tickets     GET  /api/it/tickets/mis-tickets/
      metricas        GET  /api/it/tickets/metricas/
    """

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        'folio', 'titulo', 'descripcion',
        'empleado__user__first_name', 'empleado__user__last_name',
        'empleado__codigo_empleado',
    ]
    ordering_fields = ['fecha_creacion', 'fecha_actualizacion', 'prioridad', 'estado']
    ordering = ['-fecha_creacion']

    def get_permissions(self):
        """
        - create: cualquier empleado autenticado
        - retrieve: dueño del ticket o IT
        - list/update/partial_update/destroy/cambiar_estado: IT
        - mis_tickets/metricas: autenticado
        """
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ('retrieve',):
            return [IsAuthenticated(), EsPropietarioTicketOIT()]
        if self.action in ('mis_tickets', 'metricas'):
            return [IsAuthenticated()]
        # list, update, partial_update, destroy, cambiar_estado, etc.
        return [IsAuthenticated(), EsGrupoIT()]

    def get_serializer_class(self):
        if self.action == 'create':
            return TicketCrearSerializer
        if self.action in ('update', 'partial_update'):
            return TicketActualizarITSerializer
        if self.action in ('retrieve', 'cambiar_estado'):
            return TicketDetalleSerializer
        return TicketListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related(
            'empleado__user', 'asignado_a', 'equipo'
        ).prefetch_related('historial__usuario')

        # Filtros opcionales via query params
        estado = self.request.query_params.get('estado')
        prioridad = self.request.query_params.get('prioridad')
        categoria = self.request.query_params.get('categoria')
        asignado_a = self.request.query_params.get('asignado_a')
        mis_tickets = self.request.query_params.get('mis_tickets')

        if estado:
            qs = qs.filter(estado=estado)
        if prioridad:
            qs = qs.filter(prioridad=prioridad)
        if categoria:
            qs = qs.filter(categoria=categoria)
        if asignado_a:
            qs = qs.filter(asignado_a_id=asignado_a)

        # Si el usuario NO es IT, solo ve sus propios tickets
        if not usuario_es_it(user):
            try:
                empleado = user.empleado
                qs = qs.filter(empleado=empleado)
            except AttributeError:
                return qs.none()
        elif mis_tickets == '1':
            # IT puede filtrar los tickets asignados a sí mismo
            qs = qs.filter(asignado_a=user)

        return qs

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado del ticket validando la transición.
        Solo IT puede cambiar estados.

        Body: { "nuevo_estado": "proceso", "comentario": "...", "motivo_espera": "..." }
        """
        ticket = self.get_object()
        serializer = CambioEstadoSerializer(
            data=request.data,
            context={'ticket': ticket, 'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        nuevo_estado = serializer.validated_data['nuevo_estado']
        comentario   = serializer.validated_data.get('comentario', '')
        motivo_espera = serializer.validated_data.get('motivo_espera', '')
        solucion      = serializer.validated_data.get('solucion', '')

        # Actualizar solución si se pasa al concluir
        if nuevo_estado == EstadoTicket.CONCLUIDO and solucion:
            ticket.solucion = solucion

        try:
            ticket.cambiar_estado(
                nuevo_estado=nuevo_estado,
                usuario=request.user,
                comentario=comentario,
                motivo_espera=motivo_espera,
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(
                f"Error inesperado al cambiar estado del ticket {ticket.folio}: {e}"
            )
            return Response(
                {'error': 'Ocurrió un error interno. Por favor intenta de nuevo.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            TicketDetalleSerializer(ticket, context={'request': request}).data
        )

    @action(detail=False, methods=['get'], url_path='mis-tickets')
    def mis_tickets(self, request):
        """
        Retorna los tickets del empleado autenticado.
        Accesible para cualquier usuario con perfil de empleado.
        """
        try:
            empleado = request.user.empleado
        except AttributeError:
            return Response(
                {'error': 'Tu usuario no tiene un perfil de empleado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qs = Ticket.objects.filter(empleado=empleado).select_related(
            'equipo', 'asignado_a'
        ).order_by('-fecha_creacion')

        serializer = TicketListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='metricas')
    def metricas(self, request):
        """
        Dashboard de métricas para IT.
        Retorna conteos por estado, prioridad y categoría.
        Solo IT puede acceder al resumen completo; empleados ven solo sus propias métricas.
        """
        if usuario_es_it(request.user):
            qs_base = Ticket.objects.all()
        else:
            try:
                qs_base = Ticket.objects.filter(empleado=request.user.empleado)
            except AttributeError:
                return Response({'error': 'Sin perfil de empleado.'}, status=400)

        data = {
            'por_estado': {
                estado: qs_base.filter(estado=estado).count()
                for estado, _ in EstadoTicket.choices
            },
            'por_prioridad': {
                prioridad: qs_base.filter(prioridad=prioridad).count()
                for prioridad, _ in [
                    ('critica', 'Crítica'), ('alta', 'Alta'),
                    ('media', 'Media'), ('baja', 'Baja')
                ]
            },
            'abiertos_total': qs_base.exclude(estado=EstadoTicket.CONCLUIDO).count(),
            'concluidos_ultimos_7_dias': qs_base.filter(
                estado=EstadoTicket.CONCLUIDO,
                fecha_resolucion__gte=timezone.now() - timedelta(days=7)
            ).count(),
        }
        return Response(data)


# ===========================================================================
# API: Mantenimiento
# ===========================================================================

class MantenimientoEquipoViewSet(viewsets.ModelViewSet):
    """
    CRUD de mantenimientos de equipo.
    Solo accesible para el grupo IT.
    """

    queryset = MantenimientoEquipo.objects.select_related(
        'equipo', 'registrado_por'
    ).order_by('-fecha_realizado')
    serializer_class = MantenimientoEquipoSerializer
    permission_classes = [IsAuthenticated, EsGrupoIT]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['equipo__numero_serie', 'equipo__marca', 'tecnico']
    ordering_fields = ['fecha_realizado', 'fecha_proximo']

    def get_queryset(self):
        qs = super().get_queryset()
        equipo_id = self.request.query_params.get('equipo')
        tipo = self.request.query_params.get('tipo')
        if equipo_id:
            qs = qs.filter(equipo_id=equipo_id)
        if tipo:
            qs = qs.filter(tipo_mantenimiento=tipo)
        return qs


# ===========================================================================
# Vistas Web (función-based, autenticación por sesión)
# ===========================================================================

def _requiere_it(user):
    """Decorador helper: usuario debe ser IT o superusuario."""
    return usuario_es_it(user)


@login_required
def dashboard_it_view(request):
    """
    Dashboard principal de IT con métricas de tickets e inventario.
    Accesible a todos los empleados, pero con datos completos solo para IT.
    """
    hoy = timezone.now().date()
    es_it = usuario_es_it(request.user)

    if es_it:
        tickets_abiertos = Ticket.objects.exclude(
            estado=EstadoTicket.CONCLUIDO
        ).select_related('empleado__user', 'asignado_a').order_by('prioridad', '-fecha_creacion')[:10]

        metricas = {
            estado_val: Ticket.objects.filter(estado=estado_val).count()
            for estado_val, _ in EstadoTicket.choices
        }
        equipos_alerta = EquipoComputo.objects.filter(
            Q(fecha_proximo_mantenimiento__lt=hoy) |
            Q(fecha_proximo_mantenimiento__lte=hoy + timedelta(days=7))
        ).order_by('fecha_proximo_mantenimiento')[:5]
    else:
        try:
            empleado = request.user.empleado
            tickets_abiertos = Ticket.objects.filter(
                empleado=empleado
            ).exclude(estado=EstadoTicket.CONCLUIDO).order_by('-fecha_creacion')[:10]
        except AttributeError:
            tickets_abiertos = Ticket.objects.none()
        metricas = {}
        equipos_alerta = []

    contexto = {
        'tickets_abiertos': tickets_abiertos,
        'metricas': metricas,
        'equipos_alerta': equipos_alerta,
        'es_it': es_it,
        'estados_ticket': EstadoTicket.choices,
    }
    return render(request, 'it_tickets/dashboard.html', contexto)


@login_required
def lista_tickets_view(request):
    """
    Lista de tickets con filtros por estado, prioridad y categoría.
    IT ve todos; empleados solo ven los suyos.
    """
    es_it = usuario_es_it(request.user)

    if es_it:
        qs = Ticket.objects.select_related('empleado__user', 'asignado_a', 'equipo')
    else:
        try:
            qs = Ticket.objects.filter(
                empleado=request.user.empleado
            ).select_related('empleado__user', 'equipo')
        except AttributeError:
            qs = Ticket.objects.none()

    # Filtros GET
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    categoria = request.GET.get('categoria', '')
    buscar = request.GET.get('q', '')

    if estado:
        qs = qs.filter(estado=estado)
    if prioridad:
        qs = qs.filter(prioridad=prioridad)
    if categoria:
        qs = qs.filter(categoria=categoria)
    if buscar:
        qs = qs.filter(
            Q(folio__icontains=buscar) |
            Q(titulo__icontains=buscar) |
            Q(descripcion__icontains=buscar)
        )

    qs = qs.order_by('-fecha_creacion')

    # Equipos asignados al empleado para el modal de nuevo ticket
    equipos_empleado = []
    try:
        empleado = request.user.empleado
        for eq in EquipoComputo.objects.filter(
            empleado=empleado,
            estado='activo'
        ).order_by('tipo'):
            equipos_empleado.append({
                'id': eq.id,
                'tipo': eq.tipo,
                'marca': eq.marca,
                'modelo': eq.modelo,
                'numero_serie': eq.numero_serie,
                'tiene_telefono': bool(eq.telefono_serie or eq.mac_telefono),
            })
    except AttributeError:
        pass

    import json
    contexto = {
        'tickets': qs,
        'es_it': es_it,
        'estados': EstadoTicket.choices,
        'filtro_estado': estado,
        'filtro_prioridad': prioridad,
        'filtro_categoria': categoria,
        'buscar': buscar,
        'equipos_empleado_json': json.dumps(equipos_empleado),
    }
    return render(request, 'it_tickets/lista_tickets.html', contexto)


@login_required
def detalle_ticket_view(request, pk):
    """
    Detalle de un ticket con historial de cambios de estado.
    Los empleados solo pueden ver sus propios tickets.
    """
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'empleado__user', 'asignado_a', 'equipo'
        ).prefetch_related('historial__usuario'),
        pk=pk
    )

    es_it = usuario_es_it(request.user)

    # Verificar que el empleado solo vea sus propios tickets
    if not es_it:
        try:
            if ticket.empleado.user != request.user:
                return redirect('lista_tickets_it')
        except AttributeError:
            return redirect('lista_tickets_it')

    contexto = {
        'ticket': ticket,
        'historial': ticket.historial.all(),
        'es_it': es_it,
        'estados_disponibles': [
            e for e in EstadoTicket.choices
            if ticket.puede_cambiar_a(e[0])
        ],
    }
    return render(request, 'it_tickets/detalle_ticket.html', contexto)


@login_required
@user_passes_test(_requiere_it, login_url='/dashboard/')
def inventario_view(request):
    """
    Gestión de inventario de equipos. Solo para IT.
    """
    hoy = timezone.now().date()
    equipos = EquipoComputo.objects.select_related('empleado__user').order_by(
        'estado', 'marca', 'modelo'
    )

    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        equipos = equipos.filter(estado=estado_filtro)

    contexto = {
        'equipos': equipos,
        'estados': EstadoEquipo.choices,
        'filtro_estado': estado_filtro,
        'total_activos': EquipoComputo.objects.filter(estado=EstadoEquipo.ACTIVO).count(),
        'total_mantenimiento_vencido': EquipoComputo.objects.filter(
            fecha_proximo_mantenimiento__lt=hoy
        ).count(),
    }
    return render(request, 'it_tickets/inventario.html', contexto)


@login_required
@user_passes_test(_requiere_it, login_url='/dashboard/')
def calendario_mantenimiento_view(request):
    """
    Calendario de mantenimientos próximos y vencidos. Solo para IT.
    """
    hoy = timezone.now().date()
    inicio = hoy - timedelta(days=30)
    fin = hoy + timedelta(days=60)

    mantenimientos = MantenimientoEquipo.objects.filter(
        fecha_realizado__gte=inicio
    ).select_related('equipo', 'registrado_por').order_by('fecha_realizado')

    proximos = EquipoComputo.objects.filter(
        fecha_proximo_mantenimiento__gte=hoy,
        fecha_proximo_mantenimiento__lte=fin,
    ).order_by('fecha_proximo_mantenimiento')

    vencidos = EquipoComputo.objects.filter(
        fecha_proximo_mantenimiento__lt=hoy,
        estado__in=[EstadoEquipo.ACTIVO, EstadoEquipo.MANTENIMIENTO]
    ).order_by('fecha_proximo_mantenimiento')

    contexto = {
        'mantenimientos_recientes': mantenimientos,
        'proximos': proximos,
        'vencidos': vencidos,
        'hoy': hoy,
    }
    return render(request, 'it_tickets/calendario_mantenimiento.html', contexto)
