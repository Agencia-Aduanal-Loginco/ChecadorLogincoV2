from django.contrib import admin
from .models import RegistroAsistencia


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'hora_entrada', 'hora_salida', 'horas_trabajadas', 'retardo', 'reconocimiento_facial')
    list_filter = ('fecha', 'retardo', 'reconocimiento_facial', 'justificado')
    search_fields = ('empleado__codigo_empleado', 'empleado__user__first_name', 'empleado__user__last_name')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'esta_completo', 'tiempo_trabajado_str')
    date_hierarchy = 'fecha'
    
    fieldsets = (
        ('Empleado', {
            'fields': ('empleado', 'fecha')
        }),
        ('Horarios', {
            'fields': ('hora_entrada', 'hora_salida', 'horas_trabajadas', 'tiempo_trabajado_str')
        }),
        ('Reconocimiento Facial', {
            'fields': ('reconocimiento_facial', 'foto_registro', 'confianza_reconocimiento')
        }),
        ('Ubicación', {
            'fields': ('ubicacion', 'latitud', 'longitud'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('retardo', 'justificado', 'notas', 'esta_completo')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
