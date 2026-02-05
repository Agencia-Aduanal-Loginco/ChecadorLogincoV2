from django.contrib import admin
from .models import TipoPermiso, SolicitudPermiso, HistorialPermiso


@admin.register(TipoPermiso)
class TipoPermisoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'requiere_evidencia', 'dias_maximos', 'afecta_salario', 'activo')
    list_filter = ('requiere_evidencia', 'afecta_salario', 'activo')
    search_fields = ('codigo', 'nombre', 'descripcion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    fieldsets = (
        ('Informacion General', {
            'fields': ('codigo', 'nombre', 'descripcion', 'color')
        }),
        ('Configuracion', {
            'fields': ('requiere_evidencia', 'dias_maximos', 'dias_anticipacion', 'afecta_salario')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )


class HistorialPermisoInline(admin.TabularInline):
    model = HistorialPermiso
    extra = 0
    readonly_fields = ('accion', 'usuario', 'comentarios', 'fecha')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SolicitudPermiso)
class SolicitudPermisoAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo_permiso', 'fecha_inicio', 'fecha_fin', 'estado', 'dias_solicitados', 'aprobador')
    list_filter = ('estado', 'tipo_permiso', 'fecha_inicio')
    search_fields = ('empleado__user__username', 'empleado__codigo_empleado', 'motivo')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'dias_solicitados')
    autocomplete_fields = ['empleado', 'aprobador']
    inlines = [HistorialPermisoInline]
    date_hierarchy = 'fecha_inicio'

    fieldsets = (
        ('Solicitud', {
            'fields': ('empleado', 'tipo_permiso', 'estado')
        }),
        ('Periodo', {
            'fields': ('fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin', 'dias_solicitados')
        }),
        ('Detalles', {
            'fields': ('motivo', 'evidencia')
        }),
        ('Resolucion', {
            'fields': ('aprobador', 'fecha_resolucion', 'comentarios_resolucion')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        }),
    )

    actions = ['aprobar_permisos', 'rechazar_permisos']

    def aprobar_permisos(self, request, queryset):
        from empleados.models import Empleado
        try:
            aprobador = Empleado.objects.get(user=request.user)
            count = 0
            for solicitud in queryset.filter(estado='pendiente'):
                solicitud.aprobar(aprobador, 'Aprobado desde admin')
                count += 1
            self.message_user(request, f'{count} solicitud(es) aprobada(s).')
        except Empleado.DoesNotExist:
            self.message_user(request, 'No tienes un perfil de empleado asociado.', level='error')
    aprobar_permisos.short_description = 'Aprobar permisos seleccionados'

    def rechazar_permisos(self, request, queryset):
        from empleados.models import Empleado
        try:
            aprobador = Empleado.objects.get(user=request.user)
            count = 0
            for solicitud in queryset.filter(estado='pendiente'):
                solicitud.rechazar(aprobador, 'Rechazado desde admin')
                count += 1
            self.message_user(request, f'{count} solicitud(es) rechazada(s).')
        except Empleado.DoesNotExist:
            self.message_user(request, 'No tienes un perfil de empleado asociado.', level='error')
    rechazar_permisos.short_description = 'Rechazar permisos seleccionados'


@admin.register(HistorialPermiso)
class HistorialPermisoAdmin(admin.ModelAdmin):
    list_display = ('solicitud', 'accion', 'usuario', 'fecha')
    list_filter = ('accion', 'fecha')
    search_fields = ('solicitud__empleado__user__username', 'comentarios')
    readonly_fields = ('solicitud', 'accion', 'usuario', 'comentarios', 'fecha')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
