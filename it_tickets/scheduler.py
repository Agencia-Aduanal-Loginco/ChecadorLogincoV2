"""
Scheduler de la app it_tickets.

Jobs programados:
  - alertas_mantenimiento : Lunes y Jueves a las 8:00am -> notifica al grupo IT
  - reporte_semanal_it    : Lunes a las 9:00am -> reporte semanal de equipos y tickets
  - reporte_mensual_it    : Día 1 de cada mes a las 9:00am -> reporte mensual

Usa APScheduler con DjangoJobStore (misma infraestructura que reportes/).
"""
import logging

from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

logger = logging.getLogger(__name__)


@util.close_old_connections
def job_alertas_mantenimiento():
    """
    Notifica al grupo IT sobre equipos con mantenimiento próximo (7 días)
    o ya vencido.
    """
    from it_tickets.services.notificaciones import notificar_mantenimientos_proximos
    logger.info("Ejecutando job: alertas de mantenimiento de equipos")
    try:
        total = notificar_mantenimientos_proximos(dias_anticipacion=7)
        logger.info(f"Alertas de mantenimiento: {total} equipo(s) notificado(s)")
    except Exception as e:
        logger.error(f"Error en job_alertas_mantenimiento: {e}")


@util.close_old_connections
def job_reporte_semanal_it():
    """Envía el reporte semanal de IT (lunes a las 9am)."""
    from it_tickets.services.notificaciones import enviar_reporte_semanal_it
    logger.info("Ejecutando job: reporte semanal IT")
    try:
        enviar_reporte_semanal_it()
        logger.info("Reporte semanal IT enviado exitosamente")
    except Exception as e:
        logger.error(f"Error en job_reporte_semanal_it: {e}")


@util.close_old_connections
def job_reporte_mensual_it():
    """Envía el reporte mensual de IT (día 1 de cada mes a las 9am)."""
    from it_tickets.services.notificaciones import enviar_reporte_mensual_it
    logger.info("Ejecutando job: reporte mensual IT")
    try:
        enviar_reporte_mensual_it()
        logger.info("Reporte mensual IT enviado exitosamente")
    except Exception as e:
        logger.error(f"Error en job_reporte_mensual_it: {e}")


def start_scheduler_it():
    """
    Inicializa el scheduler de IT y registra los jobs.
    Se llama desde ItTicketsConfig.ready().

    Reutiliza el DjangoJobStore ya configurado por django_apscheduler.
    Si el scheduler de reportes ya está corriendo, los jobs de IT
    se añaden al mismo store sin conflicto (los IDs son únicos).
    """
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Alertas de mantenimiento: Lunes y Jueves a las 8:00am
    scheduler.add_job(
        job_alertas_mantenimiento,
        trigger=CronTrigger(day_of_week="mon,thu", hour=8, minute=0),
        id="it_alertas_mantenimiento",
        max_instances=1,
        replace_existing=True,
        name="IT: Alertas de Mantenimiento de Equipos"
    )
    logger.info("Job programado: Alertas de mantenimiento (Lun y Jue 8:00am)")

    # Reporte semanal: Lunes a las 9:00am
    scheduler.add_job(
        job_reporte_semanal_it,
        trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="it_reporte_semanal",
        max_instances=1,
        replace_existing=True,
        name="IT: Reporte Semanal de Tickets y Equipos"
    )
    logger.info("Job programado: Reporte semanal IT (Lunes 9:00am)")

    # Reporte mensual: Día 1 de cada mes a las 9:00am
    scheduler.add_job(
        job_reporte_mensual_it,
        trigger=CronTrigger(day=1, hour=9, minute=0),
        id="it_reporte_mensual",
        max_instances=1,
        replace_existing=True,
        name="IT: Reporte Mensual de Tickets"
    )
    logger.info("Job programado: Reporte mensual IT (Día 1 de cada mes 9:00am)")

    try:
        logger.info("Iniciando scheduler de IT...")
        scheduler.start()
        logger.info("Scheduler de IT iniciado exitosamente")
    except KeyboardInterrupt:
        logger.info("Deteniendo scheduler de IT...")
        scheduler.shutdown()
    except Exception as e:
        # Si ya hay un scheduler corriendo (puede ocurrir con runserver en
        # modo debug con auto-reload), solo registramos el error y continuamos.
        logger.warning(f"No se pudo iniciar el scheduler de IT: {e}")
