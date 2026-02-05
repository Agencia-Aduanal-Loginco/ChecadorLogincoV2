"""
Comando de gestion para el scheduler de reportes.
Permite iniciar el scheduler manualmente y ver el estado de los jobs.
"""
from django.core.management.base import BaseCommand
from django_apscheduler.models import DjangoJob, DjangoJobExecution


class Command(BaseCommand):
    help = 'Gestiona el scheduler de reportes automaticos'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'start', 'list'],
            help='Accion a ejecutar: status (ver estado), start (iniciar scheduler), list (listar ejecuciones)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limite de resultados para listar ejecuciones (default: 10)'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'status':
            self.show_status()
        elif action == 'start':
            self.start_scheduler()
        elif action == 'list':
            self.list_executions(options['limit'])

    def show_status(self):
        """Muestra el estado de los jobs programados"""
        jobs = DjangoJob.objects.all()
        
        if not jobs.exists():
            self.stdout.write(self.style.WARNING('No hay jobs programados'))
            self.stdout.write('')
            self.stdout.write('Para iniciar el scheduler, ejecuta:')
            self.stdout.write('  python manage.py runserver')
            self.stdout.write('  o')
            self.stdout.write('  python manage.py scheduler start')
            return

        self.stdout.write(self.style.SUCCESS(f'Jobs programados: {jobs.count()}'))
        self.stdout.write('')
        
        for job in jobs:
            self.stdout.write(self.style.HTTP_INFO(f'Job ID: {job.id}'))
            self.stdout.write(f'  Siguiente ejecucion: {job.next_run_time}')
            
            # Obtener ultima ejecucion
            last_execution = DjangoJobExecution.objects.filter(job=job).order_by('-run_time').first()
            if last_execution:
                status_style = self.style.SUCCESS if last_execution.status == 'Success' else self.style.ERROR
                self.stdout.write(f'  Ultima ejecucion: {last_execution.run_time}')
                self.stdout.write(f'  Estado: {status_style(last_execution.status)}')
                if last_execution.exception:
                    self.stdout.write(f'  Error: {last_execution.exception[:100]}...')
            else:
                self.stdout.write('  Ultima ejecucion: Ninguna')
            
            self.stdout.write('')

    def start_scheduler(self):
        """Inicia el scheduler manualmente"""
        self.stdout.write('Iniciando scheduler de reportes...')
        
        try:
            from reportes.scheduler import start_scheduler
            start_scheduler()
            self.stdout.write(self.style.SUCCESS('Scheduler iniciado exitosamente'))
            self.stdout.write('')
            self.stdout.write('El scheduler se ejecutara en segundo plano.')
            self.stdout.write('Para ver el estado, ejecuta: python manage.py scheduler status')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al iniciar scheduler: {e}'))

    def list_executions(self, limit):
        """Lista las ultimas ejecuciones de jobs"""
        executions = DjangoJobExecution.objects.all().order_by('-run_time')[:limit]
        
        if not executions:
            self.stdout.write(self.style.WARNING('No hay ejecuciones registradas'))
            return

        self.stdout.write(self.style.SUCCESS(f'Ultimas {limit} ejecuciones:'))
        self.stdout.write('')
        
        for execution in executions:
            status_style = self.style.SUCCESS if execution.status == 'Success' else self.style.ERROR
            
            self.stdout.write(f'Job ID: {execution.job.id if execution.job else "N/A"}')
            self.stdout.write(f'  Hora: {execution.run_time}')
            self.stdout.write(f'  Estado: {status_style(execution.status)}')
            self.stdout.write(f'  Duracion: {execution.duration} segundos')
            
            if execution.exception:
                self.stdout.write(f'  Error: {execution.exception[:150]}...')
            
            self.stdout.write('')
