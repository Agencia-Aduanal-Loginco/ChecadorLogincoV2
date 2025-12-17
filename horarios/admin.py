from django.contrib import admin
from .models import Horario


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'get_dia', 'hora_entrada', 'hora_salida', 'horas_dia', 'activo')
    list_filter = ('dia_semana', 'activo')
    search_fields = ('empleado__codigo_empleado', 'empleado__user__first_name', 'empleado__user__last_name')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'horas_dia')
    
    fieldsets = (
        ('Empleado', {
            'fields': ('empleado',)
        }),
        ('Horario', {
            'fields': ('dia_semana', 'hora_entrada', 'hora_salida', 'tolerancia_minutos')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )
    
    def get_dia(self, obj):
        return obj.get_dia_semana_display()
    get_dia.short_description = 'Día'
