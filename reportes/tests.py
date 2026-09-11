from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from organizacion.models import Empresa
from reportes.models import ConfiguracionReporte


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
