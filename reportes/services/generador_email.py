import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


_TIPOS_META = {
    'diario':     ('Diario',    'Asistencia'),
    'semanal':    ('Semanal',   'Asistencia'),
    'quincenal':  ('Quincenal', 'Asistencia'),
    'inventario': ('Semanal',   'Inventario de Equipos'),
    'tickets_it': ('Semanal',   'Tickets IT'),
    'permisos':   ('Quincenal', 'Permisos Laborales'),
}

_NOMBRES_ARCHIVO = {
    'diario':     'reporte_asistencia',
    'semanal':    'reporte_asistencia',
    'quincenal':  'reporte_asistencia',
    'inventario': 'reporte_inventario',
    'tickets_it': 'reporte_tickets_it',
    'permisos':   'reporte_permisos',
}


def enviar_reporte(tipo_reporte, datos, destinatarios, archivo_excel=None, asunto_custom=None):
    """
    Envia reporte por email.

    Args:
        tipo_reporte: 'diario', 'semanal', 'quincenal', 'inventario', 'tickets_it', 'permisos'
        datos: dict con datos del reporte (debe incluir fecha_inicio y fecha_fin)
        destinatarios: queryset o lista de objetos con atributo .email
        archivo_excel: BytesIO con archivo Excel (opcional)
        asunto_custom: asunto personalizado (opcional)
    """
    template = f'reportes/email/reporte_{tipo_reporte}.html'
    html_content = render_to_string(template, datos)

    fecha_inicio = datos.get('fecha_inicio', '')
    fecha_fin = datos.get('fecha_fin', '')

    if asunto_custom:
        subject = asunto_custom
    else:
        periodo, categoria = _TIPOS_META.get(tipo_reporte, (tipo_reporte, tipo_reporte))
        subject = f'Reporte {periodo} de {categoria} - {fecha_inicio} al {fecha_fin}'

    emails_to = [d.email for d in destinatarios]
    if not emails_to:
        logger.warning('No hay destinatarios activos para el reporte %s', tipo_reporte)
        return 0

    prefijo = _NOMBRES_ARCHIVO.get(tipo_reporte, f'reporte_{tipo_reporte}')
    email = EmailMultiAlternatives(
        subject=subject,
        body=f'Reporte {tipo_reporte} del {fecha_inicio} al {fecha_fin}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=emails_to,
    )
    email.attach_alternative(html_content, "text/html")

    if archivo_excel:
        nombre = f'{prefijo}_{fecha_inicio}_{fecha_fin}.xlsx'
        email.attach(
            nombre,
            archivo_excel.getvalue(),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    email.send()
    logger.info('Reporte %s enviado a %d destinatarios', tipo_reporte, len(emails_to))
    return len(emails_to)
