from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from empleados.models import Empleado
from organizacion.models import Empresa
from reportes.models import ConfiguracionReporte
from reportes.services.calculos import obtener_datos_reporte


class ConfiguracionReporteEmpresaTests(TestCase):
    def setUp(self):
        # get_or_create: la migracion de backfill de empleados (Task 3) ya
        # crea LOGINCO en la base de datos de test antes de setUp().
        self.empresa_a, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )
        self.empresa_b = Empresa.objects.create(nombre='Otra SA', codigo='OTRA')

    def test_diario_requiere_empresa(self):
        config = ConfiguracionReporte(tipo='diario')

        with self.assertRaises(ValidationError):
            config.full_clean()

    def test_inventario_no_requiere_ni_permite_empresa(self):
        config = ConfiguracionReporte(tipo='inventario')
        config.full_clean()  # no debe lanzar excepción

        config_con_empresa = ConfiguracionReporte(tipo='inventario', empresa=self.empresa_a)
        with self.assertRaises(ValidationError):
            config_con_empresa.full_clean()

    def test_permite_una_configuracion_diaria_por_empresa(self):
        ConfiguracionReporte.objects.create(tipo='diario', empresa=self.empresa_a)
        ConfiguracionReporte.objects.create(tipo='diario', empresa=self.empresa_b)

        self.assertEqual(ConfiguracionReporte.objects.filter(tipo='diario').count(), 2)

    def test_no_permite_dos_configuraciones_diarias_para_la_misma_empresa(self):
        ConfiguracionReporte.objects.create(tipo='diario', empresa=self.empresa_a)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConfiguracionReporte.objects.create(tipo='diario', empresa=self.empresa_a)


class ObtenerDatosReporteEmpresaTests(TestCase):
    def setUp(self):
        # get_or_create: la migracion de backfill de empleados (Task 3) ya
        # crea LOGINCO en la base de datos de test antes de setUp().
        self.empresa_a, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )
        self.empresa_b = Empresa.objects.create(nombre='Otra SA', codigo='OTRA')

        user_a = User.objects.create_user(username='calc_a', password='x')
        self.empleado_a = Empleado.objects.create(
            user=user_a, codigo_empleado='CA001', empresa=self.empresa_a
        )
        user_b = User.objects.create_user(username='calc_b', password='x')
        self.empleado_b = Empleado.objects.create(
            user=user_b, codigo_empleado='CB001', empresa=self.empresa_b
        )

    def test_sin_empresa_incluye_todos_los_empleados(self):
        datos = obtener_datos_reporte(date(2026, 1, 1), date(2026, 1, 31))

        codigos = [d['codigo'] for d in datos['datos_empleados']]
        self.assertIn('CA001', codigos)
        self.assertIn('CB001', codigos)
        self.assertIsNone(datos['empresa'])

    def test_con_empresa_filtra_solo_esa_empresa(self):
        datos = obtener_datos_reporte(date(2026, 1, 1), date(2026, 1, 31), empresa=self.empresa_a)

        codigos = [d['codigo'] for d in datos['datos_empleados']]
        self.assertIn('CA001', codigos)
        self.assertNotIn('CB001', codigos)
        self.assertEqual(datos['empresa'], self.empresa_a)
