"""
Scheduler automatico de reportes usando Django APScheduler.
Reemplaza la configuracion de cron por un sistema interno de Django.
"""
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

logger = logging.getLogger(__name__)


@util.close_old_connections
def enviar_reporte_diario():
    """Job para enviar reporte diario"""
    from reportes.services.calculos import obtener_datos_reporte
    from reportes.services.generador_excel import generar_reporte_excel
    from reportes.services.generador_email import enviar_reporte
    from reportes.models import ConfiguracionReporte, LogReporte
    
    logger.info("Iniciando envio de reporte diario")
    
    try:
        # Obtener configuracion
        config = ConfiguracionReporte.objects.filter(tipo='diario', activo=True).first()
        if not config:
            logger.warning("No hay configuracion activa para reporte diario")
            return
        
        destinatarios = config.destinatarios.filter(activo=True)
        if not destinatarios.exists():
            logger.warning("No hay destinatarios activos para reporte diario")
            return
        
        # Obtener datos de hoy
        hoy = timezone.now().date()
        datos = obtener_datos_reporte(hoy, hoy)
        
        # Generar Excel si esta configurado
        archivo_excel = None
        if config.incluir_excel:
            archivo_excel = generar_reporte_excel(datos)
        
        # Enviar reporte
        num_enviados = enviar_reporte('diario', datos, destinatarios, archivo_excel=archivo_excel)
        
        # Registrar en log
        LogReporte.objects.create(
            tipo_reporte='diario',
            fecha_inicio_rango=hoy,
            fecha_fin_rango=hoy,
            destinatarios_enviados=num_enviados,
            estado='enviado'
        )
        
        logger.info(f"Reporte diario enviado exitosamente a {num_enviados} destinatarios")
        
    except Exception as e:
        logger.error(f"Error al enviar reporte diario: {e}")
        LogReporte.objects.create(
            tipo_reporte='diario',
            fecha_inicio_rango=timezone.now().date(),
            fecha_fin_rango=timezone.now().date(),
            destinatarios_enviados=0,
            estado='error',
            error_detalle=str(e)
        )


@util.close_old_connections
def enviar_reporte_semanal():
    """Job para enviar reporte semanal"""
    from reportes.services.calculos import obtener_datos_reporte
    from reportes.services.generador_excel import generar_reporte_excel
    from reportes.services.generador_email import enviar_reporte
    from reportes.models import ConfiguracionReporte, LogReporte
    
    logger.info("Iniciando envio de reporte semanal")
    
    try:
        # Obtener configuracion
        config = ConfiguracionReporte.objects.filter(tipo='semanal', activo=True).first()
        if not config:
            logger.warning("No hay configuracion activa para reporte semanal")
            return
        
        destinatarios = config.destinatarios.filter(activo=True)
        if not destinatarios.exists():
            logger.warning("No hay destinatarios activos para reporte semanal")
            return
        
        # Calcular rango de la semana (lunes a hoy)
        hoy = timezone.now().date()
        fecha_inicio = hoy - timedelta(days=hoy.weekday())
        
        # Obtener datos
        datos = obtener_datos_reporte(fecha_inicio, hoy)
        
        # Generar Excel (siempre para semanal)
        archivo_excel = generar_reporte_excel(datos)
        
        # Enviar reporte
        num_enviados = enviar_reporte('semanal', datos, destinatarios, archivo_excel=archivo_excel)
        
        # Registrar en log
        LogReporte.objects.create(
            tipo_reporte='semanal',
            fecha_inicio_rango=fecha_inicio,
            fecha_fin_rango=hoy,
            destinatarios_enviados=num_enviados,
            estado='enviado'
        )
        
        logger.info(f"Reporte semanal enviado exitosamente a {num_enviados} destinatarios")
        
    except Exception as e:
        logger.error(f"Error al enviar reporte semanal: {e}")
        LogReporte.objects.create(
            tipo_reporte='semanal',
            fecha_inicio_rango=timezone.now().date(),
            fecha_fin_rango=timezone.now().date(),
            destinatarios_enviados=0,
            estado='error',
            error_detalle=str(e)
        )


@util.close_old_connections
def enviar_reporte_quincenal():
    """Job para enviar reporte quincenal"""
    import calendar
    from reportes.services.calculos import obtener_datos_reporte
    from reportes.services.generador_excel import generar_reporte_excel
    from reportes.services.generador_email import enviar_reporte
    from reportes.models import ConfiguracionReporte, LogReporte
    
    logger.info("Iniciando envio de reporte quincenal")
    
    try:
        # Obtener configuracion
        config = ConfiguracionReporte.objects.filter(tipo='quincenal', activo=True).first()
        if not config:
            logger.warning("No hay configuracion activa para reporte quincenal")
            return
        
        destinatarios = config.destinatarios.filter(activo=True)
        if not destinatarios.exists():
            logger.warning("No hay destinatarios activos para reporte quincenal")
            return
        
        # Calcular rango quincenal
        hoy = timezone.now().date()
        if hoy.day <= 14:
            # Primera quincena (1-14)
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy.replace(day=14)
        else:
            # Segunda quincena (15-ultimo dia)
            fecha_inicio = hoy.replace(day=15)
            ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
            fecha_fin = hoy.replace(day=ultimo_dia)
        
        # Obtener datos
        datos = obtener_datos_reporte(fecha_inicio, fecha_fin)
        
        # Generar Excel (siempre para quincenal)
        archivo_excel = generar_reporte_excel(datos)
        
        # Enviar reporte
        num_enviados = enviar_reporte('quincenal', datos, destinatarios, archivo_excel=archivo_excel)
        
        # Registrar en log
        LogReporte.objects.create(
            tipo_reporte='quincenal',
            fecha_inicio_rango=fecha_inicio,
            fecha_fin_rango=fecha_fin,
            destinatarios_enviados=num_enviados,
            estado='enviado'
        )
        
        logger.info(f"Reporte quincenal enviado exitosamente a {num_enviados} destinatarios")
        
    except Exception as e:
        logger.error(f"Error al enviar reporte quincenal: {e}")
        LogReporte.objects.create(
            tipo_reporte='quincenal',
            fecha_inicio_rango=timezone.now().date(),
            fecha_fin_rango=timezone.now().date(),
            destinatarios_enviados=0,
            estado='error',
            error_detalle=str(e)
        )


@util.close_old_connections
def enviar_reporte_inventario():
    """Job semanal para reporte de inventario de equipos"""
    from reportes.services.calculos_inventario import obtener_datos_inventario
    from reportes.services.generador_excel import generar_reporte_inventario_excel
    from reportes.services.generador_email import enviar_reporte
    from reportes.models import ConfiguracionReporte, LogReporte

    logger.info("Iniciando envio de reporte de inventario")

    try:
        config = ConfiguracionReporte.objects.filter(tipo='inventario', activo=True).first()
        if not config:
            logger.warning("No hay configuracion activa para reporte de inventario")
            return

        destinatarios = config.destinatarios.filter(activo=True)
        if not destinatarios.exists():
            logger.warning("No hay destinatarios activos para reporte de inventario")
            return

        hoy = timezone.now().date()
        datos = obtener_datos_inventario()
        # Añadimos fecha_inicio y fecha_fin para el asunto del email
        datos['fecha_inicio'] = hoy
        datos['fecha_fin'] = hoy

        archivo_excel = generar_reporte_inventario_excel(datos)
        num_enviados = enviar_reporte('inventario', datos, destinatarios, archivo_excel=archivo_excel)

        LogReporte.objects.create(
            tipo_reporte='inventario',
            fecha_inicio_rango=hoy,
            fecha_fin_rango=hoy,
            destinatarios_enviados=num_enviados,
            estado='enviado'
        )
        logger.info(f"Reporte de inventario enviado exitosamente a {num_enviados} destinatarios")

    except Exception as e:
        logger.error(f"Error al enviar reporte de inventario: {e}")
        hoy = timezone.now().date()
        LogReporte.objects.create(
            tipo_reporte='inventario',
            fecha_inicio_rango=hoy,
            fecha_fin_rango=hoy,
            destinatarios_enviados=0,
            estado='error',
            error_detalle=str(e)
        )


@util.close_old_connections
def enviar_reporte_tickets_it():
    """Job semanal para reporte de tickets IT"""
    from datetime import timedelta
    from reportes.services.calculos_tickets import obtener_datos_tickets
    from reportes.services.generador_excel import generar_reporte_tickets_excel
    from reportes.services.generador_email import enviar_reporte
    from reportes.models import ConfiguracionReporte, LogReporte

    logger.info("Iniciando envio de reporte de tickets IT")

    try:
        config = ConfiguracionReporte.objects.filter(tipo='tickets_it', activo=True).first()
        if not config:
            logger.warning("No hay configuracion activa para reporte de tickets IT")
            return

        destinatarios = config.destinatarios.filter(activo=True)
        if not destinatarios.exists():
            logger.warning("No hay destinatarios activos para reporte de tickets IT")
            return

        hoy = timezone.now().date()
        fecha_inicio = hoy - timedelta(days=hoy.weekday())
        datos = obtener_datos_tickets(fecha_inicio, hoy)

        archivo_excel = generar_reporte_tickets_excel(datos)
        num_enviados = enviar_reporte('tickets_it', datos, destinatarios, archivo_excel=archivo_excel)

        LogReporte.objects.create(
            tipo_reporte='tickets_it',
            fecha_inicio_rango=fecha_inicio,
            fecha_fin_rango=hoy,
            destinatarios_enviados=num_enviados,
            estado='enviado'
        )
        logger.info(f"Reporte de tickets IT enviado exitosamente a {num_enviados} destinatarios")

    except Exception as e:
        logger.error(f"Error al enviar reporte de tickets IT: {e}")
        hoy = timezone.now().date()
        LogReporte.objects.create(
            tipo_reporte='tickets_it',
            fecha_inicio_rango=hoy,
            fecha_fin_rango=hoy,
            destinatarios_enviados=0,
            estado='error',
            error_detalle=str(e)
        )


@util.close_old_connections
def enviar_reporte_permisos():
    """Job quincenal para reporte de permisos laborales"""
    import calendar
    from reportes.services.calculos_permisos import obtener_datos_permisos
    from reportes.services.generador_excel import generar_reporte_permisos_excel
    from reportes.services.generador_email import enviar_reporte
    from reportes.models import ConfiguracionReporte, LogReporte

    logger.info("Iniciando envio de reporte de permisos")

    try:
        config = ConfiguracionReporte.objects.filter(tipo='permisos', activo=True).first()
        if not config:
            logger.warning("No hay configuracion activa para reporte de permisos")
            return

        destinatarios = config.destinatarios.filter(activo=True)
        if not destinatarios.exists():
            logger.warning("No hay destinatarios activos para reporte de permisos")
            return

        hoy = timezone.now().date()
        if hoy.day <= 14:
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy.replace(day=14)
        else:
            fecha_inicio = hoy.replace(day=15)
            ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
            fecha_fin = hoy.replace(day=ultimo_dia)

        datos = obtener_datos_permisos(fecha_inicio, fecha_fin)

        archivo_excel = generar_reporte_permisos_excel(datos)
        num_enviados = enviar_reporte('permisos', datos, destinatarios, archivo_excel=archivo_excel)

        LogReporte.objects.create(
            tipo_reporte='permisos',
            fecha_inicio_rango=fecha_inicio,
            fecha_fin_rango=fecha_fin,
            destinatarios_enviados=num_enviados,
            estado='enviado'
        )
        logger.info(f"Reporte de permisos enviado exitosamente a {num_enviados} destinatarios")

    except Exception as e:
        logger.error(f"Error al enviar reporte de permisos: {e}")
        hoy = timezone.now().date()
        LogReporte.objects.create(
            tipo_reporte='permisos',
            fecha_inicio_rango=hoy,
            fecha_fin_rango=hoy,
            destinatarios_enviados=0,
            estado='error',
            error_detalle=str(e)
        )


@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    """
    Elimina ejecuciones de jobs antiguas (por defecto 7 dias).
    Esta funcion mantiene la base de datos limpia.
    """
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


def start_scheduler():
    """
    Inicializa y configura el scheduler con los jobs de reportes.
    Se ejecuta automaticamente al iniciar Django via apps.py
    """
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Job para reporte diario - Lunes a Sabado a las 11:50am
    scheduler.add_job(
        enviar_reporte_diario,
        trigger=CronTrigger(day_of_week="mon-sat", hour=11, minute=50),
        id="reporte_diario",
        max_instances=1,
        replace_existing=True,
        name="Envio de reporte diario"
    )
    logger.info("Job programado: Reporte diario (Lun-Sab 11:50am)")
    
    # Job para reporte semanal - Viernes a las 11:50am
    scheduler.add_job(
        enviar_reporte_semanal,
        trigger=CronTrigger(day_of_week="fri", hour=11, minute=50),
        id="reporte_semanal",
        max_instances=1,
        replace_existing=True,
        name="Envio de reporte semanal"
    )
    logger.info("Job programado: Reporte semanal (Viernes 11:50am)")
    
    # Job para reporte quincenal - Dias 14 y 29 a las 11:50am
    scheduler.add_job(
        enviar_reporte_quincenal,
        trigger=CronTrigger(day="14,29", hour=11, minute=50),
        id="reporte_quincenal",
        max_instances=1,
        replace_existing=True,
        name="Envio de reporte quincenal"
    )
    logger.info("Job programado: Reporte quincenal (Dias 14 y 29, 11:50am)")
    
    # Job para reporte de inventario - Viernes a las 12:00pm
    scheduler.add_job(
        enviar_reporte_inventario,
        trigger=CronTrigger(day_of_week="fri", hour=12, minute=0),
        id="reporte_inventario",
        max_instances=1,
        replace_existing=True,
        name="Envio de reporte de inventario"
    )
    logger.info("Job programado: Reporte inventario (Viernes 12:00pm)")

    # Job para reporte de tickets IT - Viernes a las 12:05pm
    scheduler.add_job(
        enviar_reporte_tickets_it,
        trigger=CronTrigger(day_of_week="fri", hour=12, minute=5),
        id="reporte_tickets_it",
        max_instances=1,
        replace_existing=True,
        name="Envio de reporte de tickets IT"
    )
    logger.info("Job programado: Reporte tickets IT (Viernes 12:05pm)")

    # Job para reporte de permisos - Dias 14 y 29 a las 12:10pm
    scheduler.add_job(
        enviar_reporte_permisos,
        trigger=CronTrigger(day="14,29", hour=12, minute=10),
        id="reporte_permisos",
        max_instances=1,
        replace_existing=True,
        name="Envio de reporte de permisos"
    )
    logger.info("Job programado: Reporte permisos (Dias 14 y 29, 12:10pm)")

    # Job para limpiar ejecuciones antiguas - Todos los dias a las 00:00am
    scheduler.add_job(
        delete_old_job_executions,
        trigger=CronTrigger(hour=0, minute=0),
        id="delete_old_job_executions",
        max_instances=1,
        replace_existing=True,
        name="Limpieza de jobs antiguos"
    )
    logger.info("Job programado: Limpieza de ejecuciones antiguas (Diario 00:00am)")
    
    try:
        logger.info("Iniciando scheduler de reportes...")
        scheduler.start()
        logger.info("Scheduler iniciado exitosamente")
    except KeyboardInterrupt:
        logger.info("Deteniendo scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler detenido exitosamente")
