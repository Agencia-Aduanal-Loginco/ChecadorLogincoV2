from django.contrib import admin
from django.utils.html import format_html
from .models import MotivoVisita, Visita


@admin.register(MotivoVisita)
class MotivoVisitaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'requiere_autorizacion', 'activo')
    list_filter = ('requiere_autorizacion', 'activo')
    search_fields = ('nombre', 'descripcion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    fieldsets = (
        ('Informacion', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Configuracion', {
            'fields': ('requiere_autorizacion',)
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = ('codigo_corto', 'nombre_visitante', 'empresa', 'fecha_programada', 'estado', 'mostrar_qr')
    list_filter = ('estado', 'fecha_programada', 'departamento_destino')
    search_fields = ('codigo_visita', 'nombre_visitante', 'empresa', 'email', 'telefono', 'motivo')
    readonly_fields = ('codigo_visita', 'codigo_corto', 'fecha_creacion', 'fecha_actualizacion', 'mostrar_qr_grande')
    autocomplete_fields = ['departamento_destino', 'autorizado_por']
    date_hierarchy = 'fecha_programada'

    fieldsets = (
        ('Identificacion', {
            'fields': ('codigo_visita', 'codigo_corto')
        }),
        ('Datos del Visitante', {
            'fields': ('nombre_visitante', 'empresa', 'email', 'telefono', 'identificacion_tipo', 'identificacion_numero', 'foto_visitante', 'foto_identificacion')
        }),
        ('Detalles de la Visita', {
            'fields': ('motivo', 'departamento_destino')
        }),
        ('Programacion', {
            'fields': ('fecha_programada', 'hora_programada', 'duracion_estimada')
        }),
        ('Control', {
            'fields': ('estado', 'fecha_entrada', 'fecha_salida')
        }),
        ('Codigo QR', {
            'fields': ('codigo_qr', 'mostrar_qr_grande')
        }),
        ('Autorizacion', {
            'fields': ('autorizado_por', 'fecha_autorizacion', 'comentarios_autorizacion')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        }),
    )

    actions = ['autorizar_visitas', 'rechazar_visitas', 'generar_qr_visitas']

    def mostrar_qr(self, obj):
        if obj.codigo_qr:
            return format_html('<img src="{}" width="50" height="50" />', obj.codigo_qr.url)
        return '-'
    mostrar_qr.short_description = 'QR'

    def mostrar_qr_grande(self, obj):
        if obj.codigo_qr:
            return format_html('<img src="{}" width="200" height="200" />', obj.codigo_qr.url)
        return 'No generado'
    mostrar_qr_grande.short_description = 'Codigo QR'

    def autorizar_visitas(self, request, queryset):
        from empleados.models import Empleado
        try:
            empleado = Empleado.objects.get(user=request.user)
            count = 0
            for visita in queryset.filter(estado='pendiente'):
                visita.autorizar(empleado, 'Autorizado desde admin')
                count += 1
            self.message_user(request, f'{count} visita(s) autorizada(s).')
        except Empleado.DoesNotExist:
            self.message_user(request, 'No tienes un perfil de empleado asociado.', level='error')
    autorizar_visitas.short_description = 'Autorizar visitas seleccionadas'

    def rechazar_visitas(self, request, queryset):
        from empleados.models import Empleado
        try:
            empleado = Empleado.objects.get(user=request.user)
            count = 0
            for visita in queryset.filter(estado='pendiente'):
                visita.rechazar(empleado, 'Rechazado desde admin')
                count += 1
            self.message_user(request, f'{count} visita(s) rechazada(s).')
        except Empleado.DoesNotExist:
            self.message_user(request, 'No tienes un perfil de empleado asociado.', level='error')
    rechazar_visitas.short_description = 'Rechazar visitas seleccionadas'

    def generar_qr_visitas(self, request, queryset):
        count = 0
        for visita in queryset.filter(estado='autorizado'):
            if not visita.codigo_qr:
                visita.generar_qr()
                visita.save()
                count += 1
        self.message_user(request, f'{count} codigo(s) QR generado(s).')
    generar_qr_visitas.short_description = 'Generar codigos QR'
