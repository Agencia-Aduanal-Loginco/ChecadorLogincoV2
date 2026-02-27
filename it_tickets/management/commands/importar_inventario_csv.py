"""
Management command: importar_inventario_csv

Importa el inventario de equipos de cómputo desde el archivo CSV del proyecto.

Uso:
  python manage.py importar_inventario_csv /ruta/al/Invetario_Loginco_equipo.csv
  python manage.py importar_inventario_csv /ruta/al/archivo.csv --actualizar
  python manage.py importar_inventario_csv /ruta/al/archivo.csv --dry-run

Opciones:
  --actualizar   Si existe un equipo con el mismo número de serie, lo actualiza.
                 Por defecto los duplicados se omiten.
  --dry-run      Muestra qué se importaría sin guardar en la BD.
  --encoding     Encoding del archivo (default: utf-8-sig para BOM de Excel).
"""
import csv
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from empleados.models import Empleado
from it_tickets.models import EquipoComputo, TipoEquipo, EstadoEquipo


class Command(BaseCommand):
    help = 'Importa el inventario de equipos de cómputo desde un CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            'ruta_csv',
            type=str,
            help='Ruta completa al archivo CSV del inventario'
        )
        parser.add_argument(
            '--actualizar',
            action='store_true',
            default=False,
            help='Actualizar registros existentes por número de serie'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            dest='dry_run',
            help='Solo mostrar qué se importaría, sin guardar en la BD'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig',
            help='Encoding del archivo (default: utf-8-sig)'
        )

    def handle(self, *args, **options):
        ruta = options['ruta_csv']
        actualizar = options['actualizar']
        dry_run = options['dry_run']
        encoding = options['encoding']

        # Verificar que el archivo existe
        if not os.path.isfile(ruta):
            raise CommandError(f"No se encontró el archivo: {ruta}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("MODO DRY-RUN: No se guardarán cambios en la BD.\n")
            )

        self.stdout.write(f"Leyendo archivo: {ruta}")
        self.stdout.write(f"Encoding: {encoding}")
        self.stdout.write(f"Actualizar existentes: {'Sí' if actualizar else 'No'}\n")

        creados = 0
        actualizados = 0
        omitidos = 0
        errores = []

        tipo_map = {
            'desktop':   TipoEquipo.DESKTOP,
            'laptop':    TipoEquipo.LAPTOP,
            'servidor':  TipoEquipo.SERVIDOR,
            'impresora': TipoEquipo.IMPRESORA,
            'tablet':    TipoEquipo.TABLET,
        }

        try:
            with open(ruta, encoding=encoding, newline='') as f:
                reader = csv.reader(f)
                encabezado = next(reader, None)
                self.stdout.write(f"Encabezado detectado: {encabezado}\n")

                for num_fila, fila in enumerate(reader, start=2):
                    # Normalizar longitud
                    while len(fila) < 12:
                        fila.append('')

                    codigo_empleado = fila[0].strip()
                    usuario_nombre  = fila[1].strip()
                    tipo_raw        = fila[2].strip().lower()
                    numero_serie    = fila[3].strip().upper()
                    marca           = fila[4].strip()
                    modelo          = fila[5].strip()
                    col_r           = fila[6].strip().lower()
                    col_u           = fila[7].strip().lower()
                    monitores_raw   = fila[8].strip()
                    marca_monitor   = fila[9].strip()
                    telefono_serie  = fila[10].strip()
                    mac_telefono    = fila[11].strip()

                    # Validación mínima
                    if not numero_serie:
                        msg = f"Fila {num_fila}: Número de serie vacío. Omitida."
                        errores.append(msg)
                        self.stdout.write(self.style.WARNING(f"  OMITIDA: {msg}"))
                        omitidos += 1
                        continue

                    tipo = tipo_map.get(tipo_raw, TipoEquipo.DESKTOP)
                    tiene_monitor = bool(col_r == 'x' or col_u == 'x')

                    # Buscar empleado
                    empleado = None
                    if codigo_empleado:
                        try:
                            empleado = Empleado.objects.get(
                                codigo_empleado=codigo_empleado
                            )
                        except Empleado.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  Fila {num_fila}: Empleado '{codigo_empleado}' "
                                    f"no encontrado. Se guardará solo el nombre."
                                )
                            )

                    notas = ''
                    if monitores_raw and monitores_raw not in ('', ' ', 'x'):
                        notas = f"Monitores: {monitores_raw}"
                    if col_r == 'x' and col_u == 'x':
                        notas += ' (monitor externo + USB)' if notas else '(monitor externo + USB)'

                    datos_str = (
                        f"  [{numero_serie}] {marca} {modelo} "
                        f"| {usuario_nombre or codigo_empleado} "
                        f"| Tipo: {tipo} | Monitor: {'Sí' if tiene_monitor else 'No'}"
                    )

                    if dry_run:
                        existe = EquipoComputo.objects.filter(
                            numero_serie=numero_serie
                        ).exists()
                        if existe:
                            self.stdout.write(
                                f"  [ACTUALIZAR]{datos_str}" if actualizar
                                else f"  [OMITIR (duplicado)]{datos_str}"
                            )
                        else:
                            self.stdout.write(f"  [CREAR]{datos_str}")
                        continue

                    # Guardar en BD
                    datos = {
                        'empleado': empleado,
                        'usuario_nombre': usuario_nombre or codigo_empleado or 'Sin asignar',
                        'tipo': tipo,
                        'marca': marca,
                        'modelo': modelo,
                        'tiene_monitor': tiene_monitor,
                        'marca_monitor': marca_monitor,
                        'telefono_serie': telefono_serie,
                        'mac_telefono': mac_telefono,
                        'notas': notas,
                    }

                    try:
                        with transaction.atomic():
                            qs = EquipoComputo.objects.filter(numero_serie=numero_serie)
                            if qs.exists():
                                if actualizar:
                                    qs.update(**datos)
                                    actualizados += 1
                                    self.stdout.write(
                                        self.style.SUCCESS(f"  ACTUALIZADO: {datos_str}")
                                    )
                                else:
                                    omitidos += 1
                                    self.stdout.write(
                                        self.style.WARNING(f"  OMITIDO (duplicado): {datos_str}")
                                    )
                            else:
                                EquipoComputo.objects.create(
                                    numero_serie=numero_serie, **datos
                                )
                                creados += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"  CREADO: {datos_str}")
                                )
                    except Exception as e:
                        msg = f"Fila {num_fila} (serie {numero_serie}): {str(e)}"
                        errores.append(msg)
                        self.stdout.write(self.style.ERROR(f"  ERROR: {msg}"))
                        omitidos += 1

        except UnicodeDecodeError:
            # Reintentar con latin-1
            self.stdout.write(
                self.style.WARNING(
                    f"Error con encoding {encoding}. Reintentando con latin-1..."
                )
            )
            options['encoding'] = 'latin-1'
            return self.handle(*args, **options)

        # Resumen final
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("RESUMEN (DRY-RUN - sin cambios):"))
        else:
            self.stdout.write(self.style.SUCCESS("RESUMEN DE IMPORTACIÓN:"))

        self.stdout.write(f"  Creados:     {creados}")
        self.stdout.write(f"  Actualizados:{actualizados}")
        self.stdout.write(f"  Omitidos:    {omitidos}")
        self.stdout.write(f"  Errores:     {len(errores)}")

        if errores:
            self.stdout.write(self.style.ERROR("\nDETALLE DE ERRORES:"))
            for err in errores:
                self.stdout.write(self.style.ERROR(f"  - {err}"))

        if not dry_run and (creados > 0 or actualizados > 0):
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nImportación completada. "
                    f"{creados + actualizados} equipo(s) en la base de datos."
                )
            )
