from django.db import IntegrityError, transaction
from django.test import TestCase

from organizacion.models import Empresa


class EmpresaModelTests(TestCase):
    def setUp(self):
        self.loginco, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )

    def test_crea_empresa_con_nombre_y_codigo(self):
        empresa = Empresa.objects.create(nombre='Otra Empresa', codigo='OTRA')

        self.assertEqual(str(empresa), 'OTRA - Otra Empresa')
        self.assertTrue(empresa.activo)

    def test_codigo_debe_ser_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Empresa.objects.create(nombre='Otra Empresa', codigo=self.loginco.codigo)

    def test_nombre_debe_ser_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Empresa.objects.create(nombre=self.loginco.nombre, codigo='OTRO')
