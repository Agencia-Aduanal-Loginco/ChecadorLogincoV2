from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class ReportesConfig(AppConfig):
    name = 'reportes'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """Inicializa el scheduler al arrancar Django"""
        import sys
        
        # Evitar que se ejecute en comandos de migracion, shell, etc.
        # Solo ejecutar con runserver o gunicorn
        if 'runserver' in sys.argv or ('gunicorn' in sys.argv[0] if sys.argv else False):
            # Evitar ejecutar en el proceso de recarga de runserver
            if os.environ.get('RUN_MAIN') == 'true' or 'gunicorn' in sys.argv[0]:
                try:
                    # Importar aquí para evitar problemas de inicialización
                    from django.core.management.commands.runserver import Command as RunserverCommand
                    from reportes.scheduler import start_scheduler
                    
                    start_scheduler()
                    logger.info("Scheduler de reportes iniciado correctamente")
                except Exception as e:
                    logger.error(f"Error al iniciar scheduler: {e}")
