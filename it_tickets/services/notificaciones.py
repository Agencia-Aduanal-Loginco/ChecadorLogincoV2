"""
Servicio de notificaciones por email para la app it_tickets.

Centraliza toda la lógica de envío de correos para:
- Nuevo ticket creado -> grupo IT
- Ticket en espera   -> empleado que lo levantó
- Ticket concluido   -> empleado que lo levantó
- Mantenimiento próximo -> grupo IT (llamado desde el scheduler)
"""
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

# Nombre del grupo Django que representa al equipo de IT.
# Este grupo debe existir en la base de datos (se crea en la migración inicial).
GRUPO_IT = 'IT'


def _obtener_emails_grupo_it():
    """Retorna la lista de emails activos del grupo IT."""
    try:
        grupo = Group.objects.get(name=GRUPO_IT)
        emails = list(
            grupo.user_set.filter(is_active=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )
        return emails
    except Group.DoesNotExist:
        logger.warning(
            f"El grupo '{GRUPO_IT}' no existe. "
            "Créalo en el admin de Django y agrega los usuarios de IT."
        )
        return []


def _email_empleado(ticket):
    """Retorna el email del empleado que levantó el ticket."""
    try:
        return ticket.empleado.user.email
    except AttributeError:
        return None


def notificar_nuevo_ticket(ticket):
    """
    Notifica al grupo IT que se creó un nuevo ticket.
    Se llama desde la señal post_save del modelo Ticket.
    """
    destinatarios = _obtener_emails_grupo_it()
    if not destinatarios:
        logger.warning(
            f"No hay destinatarios IT para notificar el ticket {ticket.folio}"
        )
        return

    asunto = f"[IT] Nuevo ticket: {ticket.folio} - {ticket.titulo}"
    cuerpo = (
        f"Se ha creado un nuevo ticket de soporte IT.\n\n"
        f"Folio:       {ticket.folio}\n"
        f"Empleado:    {ticket.empleado.nombre_completo}\n"
        f"Categoría:   {ticket.get_categoria_display()}\n"
        f"Descripción: {ticket.descripcion}\n"
        f"Equipo:      {ticket.equipo or 'No especificado'}\n\n"
        f"Ingresa al sistema para asignar prioridad y atender el ticket.\n"
        f"Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')} (Hora CDMX)"
    )

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )
        logger.info(
            f"Notificación de nuevo ticket {ticket.folio} "
            f"enviada a {len(destinatarios)} destinatarios IT."
        )
    except Exception as e:
        logger.error(
            f"Error enviando notificación de nuevo ticket {ticket.folio}: {e}"
        )
        raise


def notificar_ticket_en_espera(ticket):
    """
    Notifica al empleado que su ticket ha sido puesto en espera.
    Incluye el motivo de la espera.
    """
    email_empleado = _email_empleado(ticket)
    if not email_empleado:
        logger.warning(
            f"El empleado del ticket {ticket.folio} no tiene email registrado."
        )
        return

    asunto = f"[IT] Tu ticket {ticket.folio} está en espera"
    cuerpo = (
        f"Hola {ticket.empleado.nombre_completo},\n\n"
        f"Tu ticket de soporte ha sido puesto en estado 'En Espera'.\n\n"
        f"Folio:         {ticket.folio}\n"
        f"Asunto:        {ticket.titulo}\n"
        f"Motivo espera: {ticket.motivo_espera or 'Ver detalles en el sistema'}\n\n"
        f"Te notificaremos cuando se reanude la atención.\n\n"
        f"Equipo IT - Loginco\n"
        f"Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')} (Hora CDMX)"
    )

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_empleado],
            fail_silently=False,
        )
        logger.info(
            f"Notificación de espera del ticket {ticket.folio} "
            f"enviada a {email_empleado}."
        )
    except Exception as e:
        logger.error(
            f"Error enviando notificación de espera {ticket.folio}: {e}"
        )
        raise


def notificar_ticket_concluido(ticket):
    """
    Notifica al empleado que su ticket ha sido resuelto.
    Incluye la descripción de la solución.
    """
    email_empleado = _email_empleado(ticket)
    if not email_empleado:
        logger.warning(
            f"El empleado del ticket {ticket.folio} no tiene email registrado."
        )
        return

    asunto = f"[IT] Tu ticket {ticket.folio} ha sido resuelto"
    cuerpo = (
        f"Hola {ticket.empleado.nombre_completo},\n\n"
        f"Tu ticket de soporte ha sido resuelto.\n\n"
        f"Folio:     {ticket.folio}\n"
        f"Asunto:    {ticket.titulo}\n"
        f"Solución:  {ticket.solucion or 'Revisada y resuelta por el equipo IT'}\n"
        f"Atendido por: "
        f"{ticket.asignado_a.get_full_name() or ticket.asignado_a.username if ticket.asignado_a else 'Equipo IT'}\n\n"
        f"Si el problema persiste, por favor abre un nuevo ticket.\n\n"
        f"Equipo IT - Loginco\n"
        f"Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')} (Hora CDMX)"
    )

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_empleado],
            fail_silently=False,
        )
        logger.info(
            f"Notificación de cierre del ticket {ticket.folio} "
            f"enviada a {email_empleado}."
        )
    except Exception as e:
        logger.error(
            f"Error enviando notificación de cierre {ticket.folio}: {e}"
        )
        raise


def notificar_mantenimientos_proximos(dias_anticipacion=7):
    """
    Envía al grupo IT la lista de equipos con mantenimiento próximo.

    Parámetro dias_anticipacion: cuántos días antes de la fecha programada
    se considera "próximo". Por defecto 7 días.

    Llamada desde el scheduler de la app.
    """
    from it_tickets.models import EquipoComputo, EstadoEquipo

    destinatarios = _obtener_emails_grupo_it()
    if not destinatarios:
        logger.warning(
            "No hay destinatarios IT para notificar mantenimientos próximos."
        )
        return 0

    hoy = timezone.now().date()
    fecha_limite = hoy + timezone.timedelta(days=dias_anticipacion)

    equipos_proximos = EquipoComputo.objects.filter(
        fecha_proximo_mantenimiento__lte=fecha_limite,
        fecha_proximo_mantenimiento__gte=hoy,
        estado__in=[EstadoEquipo.ACTIVO, EstadoEquipo.MANTENIMIENTO]
    ).order_by('fecha_proximo_mantenimiento')

    equipos_vencidos = EquipoComputo.objects.filter(
        fecha_proximo_mantenimiento__lt=hoy,
        estado__in=[EstadoEquipo.ACTIVO, EstadoEquipo.MANTENIMIENTO]
    ).order_by('fecha_proximo_mantenimiento')

    if not equipos_proximos.exists() and not equipos_vencidos.exists():
        logger.info("No hay equipos con mantenimiento próximo o vencido.")
        return 0

    # Construir el cuerpo del correo
    lineas = [
        f"Reporte de Mantenimiento de Equipos - {hoy.strftime('%d/%m/%Y')}",
        "=" * 60,
        "",
    ]

    if equipos_vencidos.exists():
        lineas.append(f"MANTENIMIENTOS VENCIDOS ({equipos_vencidos.count()} equipos):")
        lineas.append("-" * 40)
        for eq in equipos_vencidos:
            dias_vencido = (hoy - eq.fecha_proximo_mantenimiento).days
            lineas.append(
                f"  - {eq.marca} {eq.modelo} [{eq.numero_serie}] "
                f"| Usuario: {eq.usuario_nombre} "
                f"| Vencido hace {dias_vencido} día(s) "
                f"({eq.fecha_proximo_mantenimiento.strftime('%d/%m/%Y')})"
            )
        lineas.append("")

    if equipos_proximos.exists():
        lineas.append(
            f"MANTENIMIENTOS PRÓXIMOS (próximos {dias_anticipacion} días, "
            f"{equipos_proximos.count()} equipos):"
        )
        lineas.append("-" * 40)
        for eq in equipos_proximos:
            dias_restantes = (eq.fecha_proximo_mantenimiento - hoy).days
            lineas.append(
                f"  - {eq.marca} {eq.modelo} [{eq.numero_serie}] "
                f"| Usuario: {eq.usuario_nombre} "
                f"| En {dias_restantes} día(s) "
                f"({eq.fecha_proximo_mantenimiento.strftime('%d/%m/%Y')})"
            )
        lineas.append("")

    lineas.append("Ingresa al sistema para programar los mantenimientos.")
    cuerpo = "\n".join(lineas)

    asunto = (
        f"[IT] Alerta de Mantenimiento: "
        f"{equipos_vencidos.count()} vencidos, "
        f"{equipos_proximos.count()} próximos"
    )

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )
        total = equipos_proximos.count() + equipos_vencidos.count()
        logger.info(
            f"Notificación de mantenimientos enviada: "
            f"{total} equipo(s) a {len(destinatarios)} destinatario(s)."
        )
        return total
    except Exception as e:
        logger.error(f"Error enviando notificación de mantenimientos: {e}")
        raise


def enviar_reporte_semanal_it(email_destino=None):
    """
    Genera y envía el reporte semanal de IT:
    - Estado de equipos (activos, en mantenimiento, de baja)
    - Tickets de la semana (por estado y categoría)
    - Mantenimientos realizados y próximos

    Si email_destino es None, envía al grupo IT.
    """
    from it_tickets.models import EquipoComputo, Ticket, EstadoEquipo, EstadoTicket
    from datetime import timedelta

    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=7)

    destinatarios = [email_destino] if email_destino else _obtener_emails_grupo_it()
    if not destinatarios:
        logger.warning("No hay destinatarios para el reporte semanal IT.")
        return

    # Métricas de equipos
    total_equipos = EquipoComputo.objects.count()
    equipos_activos = EquipoComputo.objects.filter(estado=EstadoEquipo.ACTIVO).count()
    equipos_mantenimiento = EquipoComputo.objects.filter(
        estado=EstadoEquipo.MANTENIMIENTO
    ).count()
    equipos_baja = EquipoComputo.objects.filter(estado=EstadoEquipo.BAJA).count()

    # Métricas de tickets de la semana
    tickets_semana = Ticket.objects.filter(fecha_creacion__date__gte=inicio_semana)
    tickets_por_estado = {
        label: tickets_semana.filter(estado=valor).count()
        for valor, label in EstadoTicket.choices
    }
    tickets_concluidos_semana = tickets_semana.filter(
        estado=EstadoTicket.CONCLUIDO
    ).count()
    tickets_pendientes_total = Ticket.objects.filter(
        estado__in=[EstadoTicket.CREADO, EstadoTicket.PENDIENTE, EstadoTicket.PROCESO,
                    EstadoTicket.ESPERA]
    ).count()

    lineas = [
        f"REPORTE SEMANAL IT - Loginco",
        f"Semana del {inicio_semana.strftime('%d/%m/%Y')} al {hoy.strftime('%d/%m/%Y')}",
        "=" * 60,
        "",
        "INVENTARIO DE EQUIPOS",
        "-" * 40,
        f"  Total equipos:          {total_equipos}",
        f"  Activos:                {equipos_activos}",
        f"  En mantenimiento:       {equipos_mantenimiento}",
        f"  De baja:                {equipos_baja}",
        "",
        "TICKETS DE LA SEMANA",
        "-" * 40,
    ]
    for label, count in tickets_por_estado.items():
        lineas.append(f"  {label:<20} {count}")

    lineas += [
        "",
        f"  Concluidos esta semana: {tickets_concluidos_semana}",
        f"  Pendientes (total):     {tickets_pendientes_total}",
        "",
        "MANTENIMIENTOS",
        "-" * 40,
    ]

    # Mantenimientos vencidos
    vencidos = EquipoComputo.objects.filter(
        fecha_proximo_mantenimiento__lt=hoy
    ).count()
    proximos_7 = EquipoComputo.objects.filter(
        fecha_proximo_mantenimiento__gte=hoy,
        fecha_proximo_mantenimiento__lte=hoy + timedelta(days=7)
    ).count()
    lineas += [
        f"  Mantenimientos vencidos: {vencidos}",
        f"  Próximos (7 días):       {proximos_7}",
        "",
        "Ingresa al sistema para ver el detalle completo.",
    ]

    cuerpo = "\n".join(lineas)
    asunto = f"[IT] Reporte Semanal - {hoy.strftime('%d/%m/%Y')}"

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )
        logger.info(
            f"Reporte semanal IT enviado a {len(destinatarios)} destinatario(s)."
        )
    except Exception as e:
        logger.error(f"Error enviando reporte semanal IT: {e}")
        raise


def enviar_reporte_mensual_it(email_destino=None):
    """
    Genera y envía el reporte mensual de IT con estadísticas del mes
    anterior: tickets atendidos, pendientes, motivos de espera más frecuentes.
    """
    from it_tickets.models import Ticket, EstadoTicket, CategoriaTicket
    from datetime import timedelta
    from django.db.models import Count, Avg

    hoy = timezone.now().date()
    # Calcular inicio y fin del mes anterior
    primer_dia_mes_actual = hoy.replace(day=1)
    fin_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
    inicio_mes_anterior = fin_mes_anterior.replace(day=1)

    destinatarios = [email_destino] if email_destino else _obtener_emails_grupo_it()
    if not destinatarios:
        logger.warning("No hay destinatarios para el reporte mensual IT.")
        return

    tickets_mes = Ticket.objects.filter(
        fecha_creacion__date__gte=inicio_mes_anterior,
        fecha_creacion__date__lte=fin_mes_anterior,
    )

    total_mes = tickets_mes.count()
    concluidos = tickets_mes.filter(estado=EstadoTicket.CONCLUIDO).count()
    pendientes = tickets_mes.exclude(estado=EstadoTicket.CONCLUIDO).count()

    por_categoria = tickets_mes.values('categoria').annotate(
        total=Count('id')
    ).order_by('-total')

    lineas = [
        f"REPORTE MENSUAL IT - Loginco",
        f"Mes: {inicio_mes_anterior.strftime('%B %Y').upper()}",
        f"Periodo: {inicio_mes_anterior.strftime('%d/%m/%Y')} - "
        f"{fin_mes_anterior.strftime('%d/%m/%Y')}",
        "=" * 60,
        "",
        "RESUMEN DE TICKETS",
        "-" * 40,
        f"  Total tickets del mes:  {total_mes}",
        f"  Concluidos:             {concluidos}",
        f"  Pendientes al cierre:   {pendientes}",
        "",
        "TICKETS POR CATEGORÍA",
        "-" * 40,
    ]

    for item in por_categoria:
        categoria_label = dict(CategoriaTicket.choices).get(item['categoria'], item['categoria'])
        lineas.append(f"  {categoria_label:<25} {item['total']}")

    lineas += [
        "",
        "TICKETS EN ESPERA DEL MES",
        "-" * 40,
    ]
    en_espera = tickets_mes.filter(estado=EstadoTicket.ESPERA)
    if en_espera.exists():
        for t in en_espera.select_related('empleado__user'):
            lineas.append(
                f"  {t.folio} | {t.titulo[:40]} | "
                f"Motivo: {t.motivo_espera[:50] if t.motivo_espera else 'No especificado'}"
            )
    else:
        lineas.append("  Sin tickets en espera al cierre del mes.")

    lineas += [
        "",
        "Generado automáticamente por el Sistema IT Loginco.",
    ]

    cuerpo = "\n".join(lineas)
    asunto = (
        f"[IT] Reporte Mensual - "
        f"{inicio_mes_anterior.strftime('%B %Y').capitalize()}"
    )

    try:
        send_mail(
            subject=asunto,
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )
        logger.info(
            f"Reporte mensual IT enviado a {len(destinatarios)} destinatario(s)."
        )
    except Exception as e:
        logger.error(f"Error enviando reporte mensual IT: {e}")
        raise
