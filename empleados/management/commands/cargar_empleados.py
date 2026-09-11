"""
Comando para cargar empleados desde archivo Excel.
Uso: python manage.py cargar_empleados
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from empleados.models import Empleado
import openpyxl
import unicodedata
import re


class Command(BaseCommand):
    help = 'Carga empleados desde el archivo ploginco.xlsx'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default='ploginco.xlsx',
            help='Ruta al archivo Excel (default: ploginco.xlsx)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='Pa$$$Word2026',
            help='Contraseña para todos los usuarios'
        )
        parser.add_argument(
            '--departamento',
            type=str,
            default='General',
            help='Departamento por defecto'
        )
        parser.add_argument(
            '--empresa',
            type=str,
            default='LOGINCO',
            help='Codigo de la empresa a la que se asignaran los empleados (default: LOGINCO)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar lo que se haría sin crear registros'
        )

    def handle(self, *args, **options):
        archivo = options['archivo']
        password = options['password']
        departamento = options['departamento']
        dry_run = options['dry_run']

        from organizacion.models import Empresa
        try:
            empresa = Empresa.objects.get(codigo=options['empresa'])
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No existe una empresa con codigo "{options["empresa"]}"'))
            return

        self.stdout.write(f'Cargando empleados desde: {archivo}')

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se crearán registros'))

        try:
            wb = openpyxl.load_workbook(archivo)
            ws = wb.active
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al abrir archivo: {e}'))
            return

        creados = 0
        existentes = 0
        errores = 0

        # Saltar la primera fila (encabezado)
        for row in ws.iter_rows(min_row=2, values_only=True):
            numero = row[0]
            nombre_completo = row[1]

            if not numero or not nombre_completo:
                continue

            nombre_completo = nombre_completo.strip()

            # Generar código de empleado
            codigo = f'EMP{int(numero):03d}'

            # Generar username a partir del nombre
            username = self.generar_username(nombre_completo)

            # Separar nombre y apellidos
            partes = nombre_completo.split()
            if len(partes) >= 2:
                first_name = partes[0]
                last_name = ' '.join(partes[1:])
            else:
                first_name = nombre_completo
                last_name = ''

            self.stdout.write(f'  {codigo}: {nombre_completo} -> {username}')

            if dry_run:
                continue

            try:
                # Verificar si el usuario ya existe
                if User.objects.filter(username=username).exists():
                    self.stdout.write(self.style.WARNING(f'    Usuario {username} ya existe'))
                    existentes += 1
                    continue

                # Verificar si el código de empleado ya existe
                if Empleado.objects.filter(codigo_empleado=codigo).exists():
                    self.stdout.write(self.style.WARNING(f'    Empleado {codigo} ya existe'))
                    existentes += 1
                    continue

                # Crear usuario
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=f'{username}@loginco.com.mx'
                )

                # Crear empleado
                empleado = Empleado.objects.create(
                    user=user,
                    codigo_empleado=codigo,
                    departamento=departamento,
                    activo=True,
                    empresa=empresa,
                )

                self.stdout.write(self.style.SUCCESS(f'    Creado: {empleado}'))
                creados += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    Error: {e}'))
                errores += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Empleados creados: {creados}'))
        self.stdout.write(self.style.WARNING(f'Ya existentes: {existentes}'))
        if errores:
            self.stdout.write(self.style.ERROR(f'Errores: {errores}'))

    def generar_username(self, nombre_completo):
        """Genera un username a partir del nombre completo."""
        # Normalizar: quitar acentos
        nombre = unicodedata.normalize('NFD', nombre_completo)
        nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')

        # Convertir a minúsculas
        nombre = nombre.lower()

        # Separar en partes
        partes = nombre.split()

        if len(partes) >= 2:
            # Usar primera letra del nombre + primer apellido
            username = partes[0][0] + partes[1]
        else:
            username = partes[0]

        # Quitar caracteres especiales
        username = re.sub(r'[^a-z0-9]', '', username)

        # Limitar longitud
        username = username[:20]

        return username
