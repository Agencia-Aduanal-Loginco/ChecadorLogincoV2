from django.contrib import admin
from .models import ConfiguracionReporte, DestinatarioReporte, LogReporte


class DestinatarioInline(admin.TabularInline):
    model = DestinatarioReporte
    extra = 1


@admin.register(ConfiguracionReporte)
class ConfiguracionReporteAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'activo', 'hora_envio', 'dia_envio_semanal', 'incluir_excel', 'num_destinatarios')
    list_filter = ('activo', 'tipo')
    inlines = [DestinatarioInline]

    fieldsets = (
        ('Configuracion', {
            'fields': ('tipo', 'activo', 'hora_envio', 'asunto_email')
        }),
        ('Opciones', {
            'fields': ('dia_envio_semanal', 'incluir_excel')
        }),
    )

    def num_destinatarios(self, obj):
        return obj.destinatarios.filter(activo=True).count()
    num_destinatarios.short_description = 'Destinatarios activos'


@admin.register(LogReporte)
class LogReporteAdmin(admin.ModelAdmin):
    list_display = ('tipo_reporte', 'fecha_envio', 'fecha_inicio_rango', 'fecha_fin_rango', 'destinatarios_enviados', 'estado')
    list_filter = ('tipo_reporte', 'estado', 'fecha_envio')
    readonly_fields = ('tipo_reporte', 'fecha_inicio_rango', 'fecha_fin_rango', 'destinatarios_enviados', 'estado', 'error_detalle', 'fecha_envio')
    date_hierarchy = 'fecha_envio'
