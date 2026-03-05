import calendar
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from zoneinfo import ZoneInfo

MEXICO_TZ = ZoneInfo('America/Mexico_City')

TIPOS_ASISTENCIA = ['diario', 'semanal', 'quincenal']
TIPOS_NUEVOS = ['inventario', 'tickets_it', 'permisos']


class Command(BaseCommand):
    help = 'Envia un reporte manualmente (asistencia, inventario, tickets IT o permisos)'

    def add_arguments(self, parser):
        parser.add_argument(
            'tipo',
            choices=TIPOS_ASISTENCIA + TIPOS_NUEVOS,
            help='Tipo de reporte a enviar'
        )
        parser.add_argument(
            '--fecha-inicio',
            type=str,
            help='Fecha inicio del rango (YYYY-MM-DD). Solo aplica a reportes con rango.'
        )
        parser.add_argument(
            '--fecha-fin',
            type=str,
            help='Fecha fin del rango (YYYY-MM-DD). Solo aplica a reportes con rango.'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email de prueba (envia solo a este correo en lugar de los destinatarios configurados)'
        )
        parser.add_argument(
            '--solo-excel',
            action='store_true',
            help='Solo generar el archivo Excel y guardarlo en disco sin enviar email'
        )

    def handle(self, *args, **options):
        tipo = options['tipo']

        if tipo in TIPOS_ASISTENCIA:
            self._handle_asistencia(tipo, options)
        elif tipo == 'inventario':
            self._handle_inventario(options)
        elif tipo == 'tickets_it':
            self._handle_tickets_it(options)
        elif tipo == 'permisos':
            self._handle_permisos(options)

    # ------------------------------------------------------------------
    # Reporte de asistencia (lógica original sin cambios)
    # ------------------------------------------------------------------
    def _handle_asistencia(self, tipo, options):
        from reportes.services.calculos import obtener_datos_reporte
        from reportes.services.generador_excel import generar_reporte_excel
        from reportes.services.generador_email import enviar_reporte
        from reportes.models import ConfiguracionReporte

        hoy = timezone.now().astimezone(MEXICO_TZ).date()

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
                fecha_inicio = hoy.replace(day=15)
                ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                fecha_fin = hoy.replace(day=ultimo_dia)
        else:
            raise CommandError('No se pudo determinar el rango de fechas')

        self.stdout.write(f'Generando reporte {tipo}: {fecha_inicio} al {fecha_fin}')
        datos = obtener_datos_reporte(fecha_inicio, fecha_fin)

        self.stdout.write(f'  Empleados: {datos["total_empleados"]}')
        self.stdout.write(f'  Registros: {datos["total_registros"]}')
        self.stdout.write(f'  Dias laborales: {datos["dias_laborales"]}')

        archivo_excel = None
        if tipo in ['semanal', 'quincenal'] or options['solo_excel']:
            archivo_excel = generar_reporte_excel(datos)
            self.stdout.write(self.style.SUCCESS('  Excel generado exitosamente'))
            if options['solo_excel']:
                nombre = f'reporte_{tipo}_{fecha_inicio}_{fecha_fin}.xlsx'
                with open(nombre, 'wb') as f:
                    f.write(archivo_excel.getvalue())
                self.stdout.write(self.style.SUCCESS(f'  Archivo guardado: {nombre}'))
                return

        destinatarios = self._get_destinatarios(tipo, options, ConfiguracionReporte)
        try:
            num_enviados = enviar_reporte(tipo, datos, destinatarios, archivo_excel=archivo_excel)
            self.stdout.write(self.style.SUCCESS(f'Reporte {tipo} enviado a {num_enviados} destinatarios'))
        except Exception as e:
            raise CommandError(f'Error al enviar reporte: {e}')

    # ------------------------------------------------------------------
    # Reporte de inventario
    # ------------------------------------------------------------------
    def _handle_inventario(self, options):
        from reportes.services.calculos_inventario import obtener_datos_inventario
        from reportes.services.generador_excel import generar_reporte_inventario_excel
        from reportes.services.generador_email import enviar_reporte
        from reportes.models import ConfiguracionReporte

        hoy = timezone.now().astimezone(MEXICO_TZ).date()
        self.stdout.write(f'Generando reporte de inventario: {hoy}')

        datos = obtener_datos_inventario()
        datos['fecha_inicio'] = hoy
        datos['fecha_fin'] = hoy

        self.stdout.write(f'  Total equipos: {datos["total_equipos"]}')
        self.stdout.write(f'  Mantenimiento vencido: {len(datos["equipos_vencidos"])}')
        self.stdout.write(f'  Mantenimiento próximo: {len(datos["equipos_pronto"])}')

        archivo_excel = generar_reporte_inventario_excel(datos)
        self.stdout.write(self.style.SUCCESS('  Excel generado exitosamente'))

        if options['solo_excel']:
            nombre = f'reporte_inventario_{hoy}.xlsx'
            with open(nombre, 'wb') as f:
                f.write(archivo_excel.getvalue())
            self.stdout.write(self.style.SUCCESS(f'  Archivo guardado: {nombre}'))
            return

        destinatarios = self._get_destinatarios('inventario', options, ConfiguracionReporte)
        try:
            num_enviados = enviar_reporte('inventario', datos, destinatarios, archivo_excel=archivo_excel)
            self.stdout.write(self.style.SUCCESS(f'Reporte inventario enviado a {num_enviados} destinatarios'))
        except Exception as e:
            raise CommandError(f'Error al enviar reporte: {e}')

    # ------------------------------------------------------------------
    # Reporte de tickets IT
    # ------------------------------------------------------------------
    def _handle_tickets_it(self, options):
        from reportes.services.calculos_tickets import obtener_datos_tickets
        from reportes.services.generador_excel import generar_reporte_tickets_excel
        from reportes.services.generador_email import enviar_reporte
        from reportes.models import ConfiguracionReporte

        hoy = timezone.now().astimezone(MEXICO_TZ).date()

        if options['fecha_inicio'] and options['fecha_fin']:
            fecha_inicio = date.fromisoformat(options['fecha_inicio'])
            fecha_fin = date.fromisoformat(options['fecha_fin'])
        else:
            fecha_inicio = hoy - timedelta(days=hoy.weekday())
            fecha_fin = hoy

        self.stdout.write(f'Generando reporte tickets IT: {fecha_inicio} al {fecha_fin}')
        datos = obtener_datos_tickets(fecha_inicio, fecha_fin)

        self.stdout.write(f'  Total tickets: {datos["total_tickets"]}')
        self.stdout.write(f'  Concluidos: {datos["tickets_concluidos"]}')
        if datos['promedio_horas_resolucion']:
            self.stdout.write(f'  Promedio resolución: {datos["promedio_horas_resolucion"]} hrs')

        archivo_excel = generar_reporte_tickets_excel(datos)
        self.stdout.write(self.style.SUCCESS('  Excel generado exitosamente'))

        if options['solo_excel']:
            nombre = f'reporte_tickets_it_{fecha_inicio}_{fecha_fin}.xlsx'
            with open(nombre, 'wb') as f:
                f.write(archivo_excel.getvalue())
            self.stdout.write(self.style.SUCCESS(f'  Archivo guardado: {nombre}'))
            return

        destinatarios = self._get_destinatarios('tickets_it', options, ConfiguracionReporte)
        try:
            num_enviados = enviar_reporte('tickets_it', datos, destinatarios, archivo_excel=archivo_excel)
            self.stdout.write(self.style.SUCCESS(f'Reporte tickets IT enviado a {num_enviados} destinatarios'))
        except Exception as e:
            raise CommandError(f'Error al enviar reporte: {e}')

    # ------------------------------------------------------------------
    # Reporte de permisos
    # ------------------------------------------------------------------
    def _handle_permisos(self, options):
        from reportes.services.calculos_permisos import obtener_datos_permisos
        from reportes.services.generador_excel import generar_reporte_permisos_excel
        from reportes.services.generador_email import enviar_reporte
        from reportes.models import ConfiguracionReporte

        hoy = timezone.now().astimezone(MEXICO_TZ).date()

        if options['fecha_inicio'] and options['fecha_fin']:
            fecha_inicio = date.fromisoformat(options['fecha_inicio'])
            fecha_fin = date.fromisoformat(options['fecha_fin'])
        else:
            if hoy.day <= 14:
                fecha_inicio = hoy.replace(day=1)
                fecha_fin = hoy.replace(day=14)
            else:
                fecha_inicio = hoy.replace(day=15)
                ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                fecha_fin = hoy.replace(day=ultimo_dia)

        self.stdout.write(f'Generando reporte de permisos: {fecha_inicio} al {fecha_fin}')
        datos = obtener_datos_permisos(fecha_inicio, fecha_fin)

        self.stdout.write(f'  Total solicitudes: {datos["total_solicitudes"]}')
        self.stdout.write(f'  Aprobadas: {datos["por_estado"]["aprobado"]}')
        self.stdout.write(f'  Pendientes actuales: {len(datos["pendientes_ahora"])}')
        self.stdout.write(f'  Días aprobados: {datos["total_dias_aprobados"]}')

        archivo_excel = generar_reporte_permisos_excel(datos)
        self.stdout.write(self.style.SUCCESS('  Excel generado exitosamente'))

        if options['solo_excel']:
            nombre = f'reporte_permisos_{fecha_inicio}_{fecha_fin}.xlsx'
            with open(nombre, 'wb') as f:
                f.write(archivo_excel.getvalue())
            self.stdout.write(self.style.SUCCESS(f'  Archivo guardado: {nombre}'))
            return

        destinatarios = self._get_destinatarios('permisos', options, ConfiguracionReporte)
        try:
            num_enviados = enviar_reporte('permisos', datos, destinatarios, archivo_excel=archivo_excel)
            self.stdout.write(self.style.SUCCESS(f'Reporte permisos enviado a {num_enviados} destinatarios'))
        except Exception as e:
            raise CommandError(f'Error al enviar reporte: {e}')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_destinatarios(self, tipo, options, ConfiguracionReporte):
        if options['email']:
            class _Dest:
                def __init__(self, email):
                    self.email = email
            self.stdout.write(f'  Enviando a email de prueba: {options["email"]}')
            return [_Dest(options['email'])]
        else:
            config = ConfiguracionReporte.objects.filter(tipo=tipo, activo=True).first()
            if not config:
                raise CommandError(
                    f'No hay configuracion activa para reporte {tipo}. Cree una en el admin Django.'
                )
            destinatarios = config.destinatarios.filter(activo=True)
            if not destinatarios.exists():
                raise CommandError(f'No hay destinatarios activos para reporte {tipo}')
            self.stdout.write(f'  Destinatarios: {destinatarios.count()}')
            return destinatarios
