from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from zoneinfo import ZoneInfo

MEXICO_TZ = ZoneInfo('America/Mexico_City')


class Command(BaseCommand):
    help = 'Envia un reporte de asistencia manualmente'

    def add_arguments(self, parser):
        parser.add_argument(
            'tipo',
            choices=['diario', 'semanal', 'quincenal'],
            help='Tipo de reporte a enviar'
        )
        parser.add_argument(
            '--fecha-inicio',
            type=str,
            help='Fecha inicio del rango (YYYY-MM-DD). Si no se especifica, se calcula automaticamente.'
        )
        parser.add_argument(
            '--fecha-fin',
            type=str,
            help='Fecha fin del rango (YYYY-MM-DD). Si no se especifica, se calcula automaticamente.'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email de prueba (envia solo a este correo en lugar de los destinatarios configurados)'
        )
        parser.add_argument(
            '--solo-excel',
            action='store_true',
            help='Solo generar el archivo Excel sin enviar email'
        )

    def handle(self, *args, **options):
        from reportes.services.calculos import obtener_datos_reporte
        from reportes.services.generador_excel import generar_reporte_excel
        from reportes.services.generador_email import enviar_reporte
        from reportes.models import ConfiguracionReporte

        tipo = options['tipo']
        hoy = timezone.now().astimezone(MEXICO_TZ).date()

        # Determinar rango de fechas
        if options['fecha_inicio'] and options['fecha_fin']:
            fecha_inicio = date.fromisoformat(options['fecha_inicio'])
            fecha_fin = date.fromisoformat(options['fecha_fin'])
        elif tipo == 'diario':
            fecha_inicio = fecha_fin = hoy
        elif tipo == 'semanal':
            fecha_inicio = hoy - timedelta(days=hoy.weekday())
            fecha_fin = hoy
        elif tipo == 'quincenal':
            if hoy.day <= 14:
                fecha_inicio = hoy.replace(day=1)
                fecha_fin = hoy.replace(day=14)
            else:
                import calendar
                fecha_inicio = hoy.replace(day=15)
                ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                fecha_fin = hoy.replace(day=ultimo_dia)
        else:
            raise CommandError('No se pudo determinar el rango de fechas')

        self.stdout.write(f'Generando reporte {tipo}: {fecha_inicio} al {fecha_fin}')

        # Obtener datos
        datos = obtener_datos_reporte(fecha_inicio, fecha_fin)

        self.stdout.write(f'  Empleados: {datos["total_empleados"]}')
        self.stdout.write(f'  Registros: {datos["total_registros"]}')
        self.stdout.write(f'  Dias laborales: {datos["dias_laborales"]}')
        self.stdout.write(f'  Con retardos: {len(datos["top_retardos"])}')
        self.stdout.write(f'  Con faltas: {len(datos["empleados_con_faltas"])}')

        # Generar Excel si aplica
        archivo_excel = None
        if tipo in ['semanal', 'quincenal'] or options['solo_excel']:
            archivo_excel = generar_reporte_excel(datos)
            self.stdout.write(self.style.SUCCESS('  Excel generado exitosamente'))

            if options['solo_excel']:
                # Guardar en disco
                nombre = f'reporte_{tipo}_{fecha_inicio}_{fecha_fin}.xlsx'
                with open(nombre, 'wb') as f:
                    f.write(archivo_excel.getvalue())
                self.stdout.write(self.style.SUCCESS(f'  Archivo guardado: {nombre}'))
                return

        # Determinar destinatarios
        if options['email']:
            # Crear destinatario temporal
            class TempDestinatario:
                def __init__(self, email):
                    self.email = email
            destinatarios = [TempDestinatario(options['email'])]
            self.stdout.write(f'  Enviando a email de prueba: {options["email"]}')
        else:
            config = ConfiguracionReporte.objects.filter(tipo=tipo, activo=True).first()
            if not config:
                raise CommandError(f'No hay configuracion activa para reporte {tipo}. Cree una en el admin.')
            destinatarios = config.destinatarios.filter(activo=True)
            if not destinatarios.exists():
                raise CommandError(f'No hay destinatarios activos para reporte {tipo}')
            self.stdout.write(f'  Destinatarios: {destinatarios.count()}')

        # Enviar
        try:
            num_enviados = enviar_reporte(tipo, datos, destinatarios, archivo_excel=archivo_excel)
            self.stdout.write(self.style.SUCCESS(f'Reporte {tipo} enviado exitosamente a {num_enviados} destinatarios'))
        except Exception as e:
            raise CommandError(f'Error al enviar reporte: {e}')
