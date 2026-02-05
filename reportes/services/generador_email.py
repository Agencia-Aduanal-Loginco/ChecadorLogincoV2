import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def enviar_reporte(tipo_reporte, datos, destinatarios, archivo_excel=None, asunto_custom=None):
    """
    Envia reporte por email con SendGrid.

    Args:
        tipo_reporte: 'diario', 'semanal', o 'quincenal'
        datos: dict con datos del reporte
        destinatarios: queryset de DestinatarioReporte
        archivo_excel: BytesIO con archivo Excel (opcional)
        asunto_custom: asunto personalizado (opcional)
    """
    template = f'reportes/email/reporte_{tipo_reporte}.html'
    html_content = render_to_string(template, datos)

    fecha_inicio = datos['fecha_inicio']
    fecha_fin = datos['fecha_fin']

    if asunto_custom:
        subject = asunto_custom
    else:
        tipos_display = {
            'diario': 'Diario',
            'semanal': 'Semanal',
            'quincenal': 'Quincenal',
        }
        tipo_display = tipos_display.get(tipo_reporte, tipo_reporte)
        subject = f'Reporte {tipo_display} de Asistencia - {fecha_inicio} al {fecha_fin}'

    emails_to = [d.email for d in destinatarios]
    if not emails_to:
        logger.warning('No hay destinatarios activos para el reporte %s', tipo_reporte)
        return 0

    email = EmailMultiAlternatives(
        subject=subject,
        body=f'Reporte de asistencia del {fecha_inicio} al {fecha_fin}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=emails_to,
    )
    email.attach_alternative(html_content, "text/html")

    if archivo_excel:
        nombre = f'reporte_asistencia_{fecha_inicio}_{fecha_fin}.xlsx'
        email.attach(
            nombre,
            archivo_excel.getvalue(),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    email.send()
    logger.info('Reporte %s enviado a %d destinatarios', tipo_reporte, len(emails_to))
    return len(emails_to)
