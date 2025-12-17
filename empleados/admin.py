from django.contrib import admin
from .models import Empleado


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('codigo_empleado', 'get_nombre', 'departamento', 'puesto', 'activo', 'tiene_rostro_registrado')
    list_filter = ('activo', 'departamento', 'fecha_ingreso')
    search_fields = ('codigo_empleado', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'tiene_rostro_registrado')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Información del Empleado', {
            'fields': ('codigo_empleado', 'departamento', 'puesto', 'horas_semana', 'fecha_ingreso')
        }),
        ('Reconocimiento Facial', {
            'fields': ('foto_rostro', 'tiene_rostro_registrado')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )
    
    def get_nombre(self, obj):
        return obj.nombre_completo
    get_nombre.short_description = 'Nombre'
