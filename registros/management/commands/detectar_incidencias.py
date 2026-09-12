from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from horarios.services import obtener_horario_del_dia
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
        ahora_mexico = timezone.now().astimezone(MEXICO_TZ)

        if options['fecha']:
            fecha_revisar = datetime.strptime(options['fecha'], '%Y-%m-%d').date()
        else:
            fecha_revisar = (ahora_mexico - timedelta(days=1)).date()

        self.stdout.write(f"Revisando registros del día: {fecha_revisar}")

        registros = RegistroAsistencia.objects.filter(
            Q(fecha=fecha_revisar) |
            Q(
                fecha__lt=fecha_revisar,
                hora_entrada__isnull=False,
                hora_salida__isnull=True,
                incidencia='ninguna',
            )
        )

        total_registros = registros.count()
        registros_con_incidencia = 0
        registros_completos = 0
        registros_nocturnos_en_curso = 0

        for registro in registros:
            if self._es_turno_nocturno_en_curso(registro, ahora_mexico):
                registros_nocturnos_en_curso += 1
                self.stdout.write(
                    f"  🌙 {registro.empleado.codigo_empleado}: turno nocturno aún en "
                    "curso, se revisará más tarde"
                )
                continue

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

        if registros_nocturnos_en_curso:
            self.stdout.write(f"🌙 Turnos nocturnos aún en curso: {registros_nocturnos_en_curso}")

        if registros_con_incidencia > 0:
            self.stdout.write(self.style.ERROR(f"✗ Registros con incidencia: {registros_con_incidencia}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ No se encontraron incidencias"))

        self.stdout.write("="*60)
        self.stdout.write(self.style.SUCCESS(f"\n✓ Proceso completado exitosamente"))

    def _es_turno_nocturno_en_curso(self, registro, ahora_mexico):
        """True si el registro es un turno nocturno que aún no debería haber cerrado."""
        if not registro.hora_entrada or registro.hora_salida:
            return False

        horario_info = obtener_horario_del_dia(registro.empleado, registro.fecha)
        if not horario_info or not getattr(horario_info['objeto'], 'cruza_medianoche', False):
            return False

        hora_salida_esperada = datetime.combine(
            registro.fecha + timedelta(days=1),
            horario_info['hora_salida'],
            tzinfo=MEXICO_TZ
        )
        limite = hora_salida_esperada + timedelta(minutes=horario_info['tolerancia_minutos'])
        return ahora_mexico < limite
