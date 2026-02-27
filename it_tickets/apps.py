"""
Configuración de la app it_tickets.

El método ready() registra el grupo IT en la base de datos si no existe,
y arranca el scheduler de mantenimientos junto con el scheduler de reportes.
"""
import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ItTicketsConfig(AppConfig):
    name = 'it_tickets'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'IT - Tickets y Equipos'

    def ready(self):
        """
        Arranca el scheduler de alertas de mantenimiento.
        Usa el mismo patrón que ReportesConfig para evitar ejecución
        en comandos de migraciones o management commands.
        """
        import sys

        # Importar señales (el módulo signals.py se importa aquí para que
        # los decoradores @receiver se registren correctamente al inicio)
        # En este proyecto las señales están en models.py (patrón existente),
        # así que no necesitamos un signals.py separado.

        if 'runserver' in sys.argv or ('gunicorn' in sys.argv[0] if sys.argv else False):
            if os.environ.get('RUN_MAIN') == 'true' or 'gunicorn' in sys.argv[0]:
                try:
                    from it_tickets.scheduler import start_scheduler_it
                    start_scheduler_it()
                    logger.info("Scheduler de IT (mantenimientos) iniciado correctamente")
                except Exception as e:
                    logger.error(f"Error al iniciar scheduler de IT: {e}")
