import logging

from django.contrib import admin, messages
from django.core.mail import send_mail
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.urls import reverse

from .models import Empleado

logger = logging.getLogger(__name__)

# Contraseña genérica que se comunica a todos los empleados
_CREDENCIAL_PASSWORD = 'Pa$$$Word2026'


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('codigo_empleado', 'get_nombre', 'departamento', 'puesto', 'activo', 'tiene_rostro_registrado', 'acciones_rostro')
    list_filter = ('activo', 'departamento', 'fecha_ingreso', 'departamento_obj')
    search_fields = ('codigo_empleado', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'tiene_rostro_registrado')
    autocomplete_fields = ['departamento_obj', 'supervisor_directo']
    actions = ['eliminar_rostros_seleccionados', 'enviar_credenciales']

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

    @admin.action(description='📧 Enviar credenciales de acceso por correo')
    def enviar_credenciales(self, request, queryset):
        """
        Acción masiva de dos pasos:
        1. Muestra lista de empleados con sus emails antes de enviar.
        2. Al confirmar, envía correo a cada uno con su usuario y la contraseña.
        """
        queryset = queryset.select_related('user')

        if 'aplicar' in request.POST:
            # --- Paso 2: enviar correos ---
            enviados = 0
            sin_email = []
            errores = []

            for empleado in queryset:
                email = empleado.user.email.strip()
                if not email:
                    sin_email.append(empleado.nombre_completo)
                    continue
                try:
                    html_body = render_to_string(
                        'emails/credenciales_acceso.html',
                        {
                            'nombre': empleado.nombre_completo,
                            'username': empleado.user.username,
                            'password': _CREDENCIAL_PASSWORD,
                        },
                        request=request,
                    )
                    send_mail(
                        subject='Tus credenciales de acceso — Sistema Checador Loginco',
                        message=(
                            f'Hola {empleado.nombre_completo},\n\n'
                            f'Usuario: {empleado.user.username}\n'
                            f'Contraseña: {_CREDENCIAL_PASSWORD}\n\n'
                            'Loginco'
                        ),
                        from_email=None,  # usa DEFAULT_FROM_EMAIL
                        recipient_list=[email],
                        html_message=html_body,
                        fail_silently=False,
                    )
                    enviados += 1
                except Exception as exc:
                    logger.exception(
                        'Error al enviar credenciales a %s <%s>', empleado.nombre_completo, email
                    )
                    errores.append(f'{empleado.nombre_completo} ({email}): {exc}')

            if enviados:
                self.message_user(
                    request,
                    f'{enviados} correo(s) enviado(s) correctamente.',
                    level=messages.SUCCESS,
                )
            if sin_email:
                self.message_user(
                    request,
                    f'Sin dirección de correo (omitidos): {", ".join(sin_email)}.',
                    level=messages.WARNING,
                )
            for err in errores:
                self.message_user(request, f'Error: {err}', level=messages.ERROR)
            return  # regresa al changelist

        # --- Paso 1: página de confirmación ---
        con_email = [e for e in queryset if e.user.email.strip()]
        sin_email = [e for e in queryset if not e.user.email.strip()]

        return render(request, 'admin/empleados/confirmar_envio_credenciales.html', {
            'empleados_con_email': con_email,
            'empleados_sin_email': sin_email,
            'action_name': 'enviar_credenciales',
            'opts': self.model._meta,
            'ACTION_CHECKBOX_NAME': admin.helpers.ACTION_CHECKBOX_NAME,
            'password': _CREDENCIAL_PASSWORD,
        })
