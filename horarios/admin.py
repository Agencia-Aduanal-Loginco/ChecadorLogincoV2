from django.contrib import admin
from .models import TipoHorario, AsignacionHorario, Horario


@admin.register(TipoHorario)
class TipoHorarioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'hora_entrada', 'hora_salida', 'tolerancia_minutos', 'tiene_comida', 'activo')
    list_filter = ('activo', 'tiene_comida')
    search_fields = ('nombre', 'codigo')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    fieldsets = (
        ('Identificacion', {
            'fields': ('nombre', 'codigo', 'descripcion', 'color')
        }),
        ('Horario', {
            'fields': ('hora_entrada', 'hora_salida', 'tolerancia_minutos')
        }),
        ('Comida', {
            'fields': ('tiene_comida', 'hora_inicio_comida', 'hora_fin_comida')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )


@admin.register(AsignacionHorario)
class AsignacionHorarioAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'fecha', 'tipo_horario', 'creado_por')
    list_filter = ('tipo_horario', 'fecha')
    search_fields = ('empleado__codigo_empleado', 'empleado__user__first_name', 'empleado__user__last_name')
    autocomplete_fields = ['empleado', 'tipo_horario']
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    date_hierarchy = 'fecha'


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
        ('Comida', {
            'fields': ('tiene_comida', 'hora_inicio_comida', 'hora_fin_comida')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )

    def get_dia(self, obj):
        return obj.get_dia_semana_display()
    get_dia.short_description = 'Dia'
