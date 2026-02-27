"""
Configuración del admin de Django para la app it_tickets.

Diseño:
- EquipoComputoAdmin    -> Inventario con acciones masivas y filtros ricos
- TicketAdmin           -> Tickets con inline de historial (solo lectura)
- HistorialTicketAdmin  -> Solo lectura, acceso de auditoría
- MantenimientoAdmin    -> Registro de mantenimientos con filtros por equipo
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    EquipoComputo, Ticket, HistorialTicket, MantenimientoEquipo,
    EstadoEquipo, EstadoTicket, TipoMantenimiento,
)


# ---------------------------------------------------------------------------
# Inline: Historial de Ticket (solo lectura en el admin de Ticket)
# ---------------------------------------------------------------------------

class HistorialTicketInline(admin.TabularInline):
    model = HistorialTicket
    extra = 0
    readonly_fields = [
        'estado_anterior', 'estado_nuevo', 'usuario', 'comentario', 'fecha'
    ]
    can_delete = False
    verbose_name = 'Entrada de Historial'
    verbose_name_plural = 'Historial de Cambios'

    def has_add_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Inline: Mantenimientos del Equipo
# ---------------------------------------------------------------------------

class MantenimientoEquipoInline(admin.TabularInline):
    model = MantenimientoEquipo
    extra = 0
    fields = [
        'tipo_mantenimiento', 'fecha_realizado', 'fecha_proximo',
        'tecnico', 'costo'
    ]
    readonly_fields = ['fecha_creacion']
    ordering = ['-fecha_realizado']


# ---------------------------------------------------------------------------
# Admin: EquipoComputo
# ---------------------------------------------------------------------------

@admin.register(EquipoComputo)
class EquipoComputoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_serie', 'marca', 'modelo', 'tipo', 'usuario_nombre',
        'empleado', 'estado_badge', 'tiene_monitor',
        'fecha_proximo_mantenimiento', 'alerta_mantenimiento',
    ]
    list_filter = ['estado', 'tipo', 'marca', 'tiene_monitor']
    search_fields = [
        'numero_serie', 'marca', 'modelo', 'usuario_nombre',
        'empleado__codigo_empleado', 'empleado__user__first_name',
        'empleado__user__last_name',
    ]
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    list_select_related = ['empleado__user']
    inlines = [MantenimientoEquipoInline]
    date_hierarchy = 'fecha_proximo_mantenimiento'
    ordering = ['marca', 'modelo']
    actions = ['marcar_activo', 'marcar_baja', 'marcar_mantenimiento']

    fieldsets = (
        ('Identificación', {
            'fields': (
                'numero_serie', 'tipo', 'marca', 'modelo',
            )
        }),
        ('Asignación', {
            'fields': ('empleado', 'usuario_nombre')
        }),
        ('Periféricos y Teléfono', {
            'fields': (
                'tiene_monitor', 'marca_monitor',
                'telefono_serie', 'mac_telefono',
            ),
            'classes': ('collapse',),
        }),
        ('Estado y Mantenimiento', {
            'fields': (
                'estado',
                'fecha_ultimo_mantenimiento',
                'fecha_proximo_mantenimiento',
            )
        }),
        ('Notas', {
            'fields': ('notas',),
            'classes': ('collapse',),
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )

    def estado_badge(self, obj):
        colores = {
            EstadoEquipo.ACTIVO: '#28a745',
            EstadoEquipo.MANTENIMIENTO: '#ffc107',
            EstadoEquipo.BAJA: '#dc3545',
        }
        color = colores.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def alerta_mantenimiento(self, obj):
        if obj.mantenimiento_vencido:
            return format_html('<span style="color:red;font-weight:bold;">VENCIDO</span>')
        if obj.requiere_mantenimiento_pronto:
            return format_html('<span style="color:orange;">Próximo</span>')
        return format_html('<span style="color:green;">OK</span>')
    alerta_mantenimiento.short_description = 'Mantenimiento'

    @admin.action(description='Marcar como Activo')
    def marcar_activo(self, request, queryset):
        count = queryset.update(estado=EstadoEquipo.ACTIVO)
        self.message_user(request, f"{count} equipo(s) marcado(s) como Activo.")

    @admin.action(description='Marcar como De Baja')
    def marcar_baja(self, request, queryset):
        count = queryset.update(estado=EstadoEquipo.BAJA)
        self.message_user(request, f"{count} equipo(s) marcado(s) como De Baja.")

    @admin.action(description='Marcar como En Mantenimiento')
    def marcar_mantenimiento(self, request, queryset):
        count = queryset.update(estado=EstadoEquipo.MANTENIMIENTO)
        self.message_user(request, f"{count} equipo(s) marcado(s) como En Mantenimiento.")


# ---------------------------------------------------------------------------
# Admin: Ticket
# ---------------------------------------------------------------------------

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'folio', 'titulo_corto', 'empleado', 'categoria',
        'prioridad_badge', 'estado_badge', 'asignado_a',
        'fecha_creacion', 'tiempo_resolucion_horas',
    ]
    list_filter = ['estado', 'prioridad', 'categoria', 'asignado_a']
    search_fields = [
        'folio', 'titulo', 'descripcion',
        'empleado__user__first_name', 'empleado__user__last_name',
        'empleado__codigo_empleado',
    ]
    readonly_fields = [
        'folio', 'fecha_creacion', 'fecha_actualizacion', 'fecha_resolucion',
        'tiempo_resolucion_horas',
    ]
    list_select_related = ['empleado__user', 'asignado_a']
    inlines = [HistorialTicketInline]
    date_hierarchy = 'fecha_creacion'
    ordering = ['-fecha_creacion']

    fieldsets = (
        ('Identificación', {
            'fields': ('folio', 'titulo', 'descripcion', 'categoria')
        }),
        ('Participantes', {
            'fields': ('empleado', 'asignado_a', 'equipo')
        }),
        ('Gestión IT', {
            'fields': ('prioridad', 'estado', 'motivo_espera', 'solucion')
        }),
        ('Fechas', {
            'fields': (
                'fecha_creacion', 'fecha_actualizacion',
                'fecha_resolucion', 'tiempo_resolucion_horas'
            ),
            'classes': ('collapse',),
        }),
    )

    def titulo_corto(self, obj):
        return obj.titulo[:50] + ('...' if len(obj.titulo) > 50 else '')
    titulo_corto.short_description = 'Título'

    def prioridad_badge(self, obj):
        if not obj.prioridad:
            return format_html('<span style="color:#aaa;">Sin asignar</span>')
        colores = {
            'critica': '#721c24',
            'alta':    '#dc3545',
            'media':   '#856404',
            'baja':    '#155724',
        }
        color = colores.get(obj.prioridad, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            color, obj.get_prioridad_display()
        )
    prioridad_badge.short_description = 'Prioridad'

    def estado_badge(self, obj):
        colores = {
            EstadoTicket.CREADO:    '#17a2b8',
            EstadoTicket.PENDIENTE: '#ffc107',
            EstadoTicket.PROCESO:   '#007bff',
            EstadoTicket.ESPERA:    '#fd7e14',
            EstadoTicket.CONCLUIDO: '#28a745',
        }
        color = colores.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def tiempo_resolucion_horas(self, obj):
        horas = obj.tiempo_resolucion_horas
        if obj.estado == EstadoTicket.CONCLUIDO:
            return f"{horas} h"
        return f"{horas} h (abierto)"
    tiempo_resolucion_horas.short_description = 'Tiempo (h)'


# ---------------------------------------------------------------------------
# Admin: HistorialTicket (solo lectura, para auditoría)
# ---------------------------------------------------------------------------

@admin.register(HistorialTicket)
class HistorialTicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket', 'estado_anterior', 'estado_nuevo',
        'usuario', 'comentario_corto', 'fecha'
    ]
    list_filter = ['estado_nuevo', 'estado_anterior']
    search_fields = ['ticket__folio', 'usuario__username', 'comentario']
    readonly_fields = [
        'ticket', 'estado_anterior', 'estado_nuevo',
        'usuario', 'comentario', 'fecha'
    ]
    ordering = ['-fecha']

    def comentario_corto(self, obj):
        return obj.comentario[:60] + ('...' if len(obj.comentario) > 60 else '')
    comentario_corto.short_description = 'Comentario'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ---------------------------------------------------------------------------
# Admin: MantenimientoEquipo
# ---------------------------------------------------------------------------

@admin.register(MantenimientoEquipo)
class MantenimientoEquipoAdmin(admin.ModelAdmin):
    list_display = [
        'equipo', 'tipo_mantenimiento', 'fecha_realizado',
        'fecha_proximo', 'tecnico', 'costo', 'registrado_por',
    ]
    list_filter = ['tipo_mantenimiento', 'equipo__marca']
    search_fields = [
        'equipo__numero_serie', 'equipo__marca',
        'tecnico', 'descripcion',
    ]
    readonly_fields = ['fecha_creacion', 'registrado_por']
    list_select_related = ['equipo', 'registrado_por']
    ordering = ['-fecha_realizado']

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
