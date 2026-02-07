from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Empleado


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('codigo_empleado', 'get_nombre', 'departamento', 'puesto', 'activo', 'tiene_rostro_registrado', 'acciones_rostro')
    list_filter = ('activo', 'departamento', 'fecha_ingreso', 'departamento_obj')
    search_fields = ('codigo_empleado', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'tiene_rostro_registrado')
    autocomplete_fields = ['departamento_obj', 'supervisor_directo']
    actions = ['eliminar_rostros_seleccionados']

    fieldsets = (
        ('Usuario', {
            'fields': ('user',)
        }),
        ('Informacion del Empleado', {
            'fields': ('codigo_empleado', 'departamento', 'departamento_obj', 'supervisor_directo', 'puesto', 'horas_semana', 'fecha_ingreso')
        }),
        ('Horarios Predeterminados', {
            'fields': ('horario_predeterminado', 'horario_sabado', 'descansa_sabado', 'horario_domingo', 'descansa_domingo'),
            'description': 'Horario predeterminado aplica de Lunes a Viernes. Sábado y Domingo se configuran por separado.'
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
    
    def acciones_rostro(self, obj):
        """Botones de acción para gestionar el rostro"""
        registro_url = reverse('empleados:register_face', args=[obj.pk])
        
        if obj.tiene_rostro_registrado:
            return format_html(
                '<a class="button" href="{}" style="padding:5px 10px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:3px; margin-right:5px;">'
                '<i class="fas fa-camera"></i> Ver/Actualizar</a>'
                '<span style="color:#28a745; font-weight:bold;"><i class="fas fa-check-circle"></i> Activo</span>',
                registro_url
            )
        else:
            return format_html(
                '<a class="button" href="{}" style="padding:5px 10px; background-color:#2196F3; color:white; text-decoration:none; border-radius:3px;">'
                '<i class="fas fa-camera"></i> Registrar Rostro</a>',
                registro_url
            )
    acciones_rostro.short_description = 'Gestión de Rostro'
    
    def eliminar_rostros_seleccionados(self, request, queryset):
        """Acción masiva para eliminar rostros de múltiples empleados"""
        count = 0
        for empleado in queryset:
            if empleado.tiene_rostro_registrado:
                empleado.eliminar_rostro()
                count += 1
        
        if count == 0:
            self.message_user(request, 'Ningún empleado seleccionado tenía rostro registrado.')
        elif count == 1:
            self.message_user(request, 'Se eliminó el rostro de 1 empleado.')
        else:
            self.message_user(request, f'Se eliminaron los rostros de {count} empleados.')
    
    eliminar_rostros_seleccionados.short_description = 'Eliminar rostros faciales de empleados seleccionados'
