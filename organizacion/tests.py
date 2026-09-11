from django.db import IntegrityError, transaction
from django.test import TestCase

from organizacion.models import Empresa


class EmpresaModelTests(TestCase):
    def test_crea_empresa_con_nombre_y_codigo(self):
        empresa = Empresa.objects.create(nombre='Loginco', codigo='LOGINCO')

        self.assertEqual(str(empresa), 'LOGINCO - Loginco')
        self.assertTrue(empresa.activo)

    def test_codigo_debe_ser_unico(self):
        Empresa.objects.create(nombre='Loginco', codigo='LOGINCO')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Empresa.objects.create(nombre='Otra Empresa', codigo='LOGINCO')

    def test_nombre_debe_ser_unico(self):
        Empresa.objects.create(nombre='Loginco', codigo='LOGINCO')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Empresa.objects.create(nombre='Loginco', codigo='OTRO')
