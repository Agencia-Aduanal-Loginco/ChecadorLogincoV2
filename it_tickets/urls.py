"""
URLs de la app it_tickets.

Se incluye desde checador/urls.py con:
    path('', include('it_tickets.urls', namespace='it_tickets'))

Rutas resultantes:
  API REST:
    GET/POST   /api/it/equipos/
    POST       /api/it/equipos/importar-csv/
    GET        /api/it/equipos/resumen/
    GET/POST   /api/it/tickets/
    GET        /api/it/tickets/mis-tickets/
    GET        /api/it/tickets/metricas/
    POST       /api/it/tickets/{id}/cambiar-estado/
    GET/POST   /api/it/mantenimientos/

  Vistas web:
    GET  /it/                              -> Dashboard IT
    GET  /it/tickets/                      -> Lista de tickets
    GET  /it/tickets/{id}/                 -> Detalle de ticket
    GET  /it/inventario/                   -> Inventario de equipos
    GET  /it/mantenimiento/calendario/     -> Calendario de mantenimientos
    GET  /it/equipos/{id}/detalle/         -> Detalle público del equipo (QR)
    GET  /it/equipos/imprimir-qrs/         -> Impresión A4 de todos los QRs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EquipoComputoViewSet,
    TicketViewSet,
    MantenimientoEquipoViewSet,
    dashboard_it_view,
    lista_tickets_view,
    detalle_ticket_view,
    inventario_view,
    calendario_mantenimiento_view,
    equipo_detalle_qr_view,
    imprimir_qrs_view,
)

app_name = 'it_tickets'

# --- Router DRF ---
router = DefaultRouter()
router.register(r'equipos', EquipoComputoViewSet, basename='equipo')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'mantenimientos', MantenimientoEquipoViewSet, basename='mantenimiento')

urlpatterns = [
    # API REST bajo /api/it/
    path('api/it/', include(router.urls)),

    # Vistas web bajo /it/
    path('it/', dashboard_it_view, name='dashboard_it'),
    path('it/tickets/', lista_tickets_view, name='lista_tickets_it'),
    path('it/tickets/<int:pk>/', detalle_ticket_view, name='detalle_ticket_it'),
    path('it/inventario/', inventario_view, name='inventario_it'),
    path('it/mantenimiento/calendario/', calendario_mantenimiento_view, name='calendario_mantenimiento'),
    # QR: imprimir antes que el detalle para evitar conflicto con int
    path('it/equipos/imprimir-qrs/', imprimir_qrs_view, name='imprimir_qrs'),
    path('it/equipos/<int:equipo_id>/detalle/', equipo_detalle_qr_view, name='equipo_detalle_qr'),
]
