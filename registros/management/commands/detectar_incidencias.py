from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo
from registros.models import RegistroAsistencia

MEXICO_TZ = ZoneInfo('America/Mexico_City')


class Command(BaseCommand):
    help = 'Detecta y marca incidencias en registros de asistencia del día anterior'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha específica a revisar (YYYY-MM-DD). Por defecto: día anterior',
        )

    def handle(self, *args, **options):
        # Determinar fecha a revisar
        if options['fecha']:
            from datetime import datetime
            fecha_revisar = datetime.strptime(options['fecha'], '%Y-%m-%d').date()
        else:
            # Día anterior en zona horaria de México
            ahora_mexico = timezone.now().astimezone(MEXICO_TZ)
            fecha_revisar = (ahora_mexico - timedelta(days=1)).date()

        self.stdout.write(f"Revisando registros del día: {fecha_revisar}")

        # Obtener todos los registros del día
        registros = RegistroAsistencia.objects.filter(fecha=fecha_revisar)
        
        total_registros = registros.count()
        registros_con_incidencia = 0
        registros_completos = 0

        for registro in registros:
            # Calcular incidencias
            registro.calcular_incidencias()
            registro.save()

            if registro.incidencia != 'ninguna':
                registros_con_incidencia += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  {registro.empleado.codigo_empleado} - {registro.empleado.nombre_completo}: "
                        f"{registro.get_incidencia_display()} - {registro.descripcion_incidencia}"
                    )
                )
            else:
                registros_completos += 1

        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"Total de registros revisados: {total_registros}")
        self.stdout.write(self.style.SUCCESS(f"✓ Registros completos: {registros_completos}"))
        
        if registros_con_incidencia > 0:
            self.stdout.write(self.style.ERROR(f"✗ Registros con incidencia: {registros_con_incidencia}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ No se encontraron incidencias"))
        
        self.stdout.write("="*60)
        self.stdout.write(self.style.SUCCESS(f"\n✓ Proceso completado exitosamente"))
