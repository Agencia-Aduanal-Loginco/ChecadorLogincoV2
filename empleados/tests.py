from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from empleados.models import Empleado
from organizacion.models import Empresa


class EmpleadoEmpresaRequeridaTests(TestCase):
    def setUp(self):
        # get_or_create porque la migración de backfill (0006) ya crea la
        # empresa "Loginco" al construir la base de datos de pruebas.
        self.empresa, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )

    def test_empleado_requiere_empresa(self):
        user = User.objects.create_user(username='sinempresa', password='x')
        empleado = Empleado(user=user, codigo_empleado='SE001')

        with self.assertRaises(ValidationError):
            empleado.full_clean()

    def test_empleado_se_crea_correctamente_con_empresa(self):
        user = User.objects.create_user(username='conempresa', password='x')
        empleado = Empleado.objects.create(
            user=user, codigo_empleado='CE001', empresa=self.empresa
        )

        self.assertEqual(empleado.empresa, self.empresa)
