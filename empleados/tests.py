from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

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
        empleado = Empleado(user=user, codigo_empleado='SE001', departamento='Ventas')

        with self.assertRaises(ValidationError):
            empleado.full_clean()

    def test_empleado_se_crea_correctamente_con_empresa(self):
        user = User.objects.create_user(username='conempresa', password='x')
        empleado = Empleado.objects.create(
            user=user, codigo_empleado='CE001', empresa=self.empresa
        )

        self.assertEqual(empleado.empresa, self.empresa)


class RegistroConEmpresaTests(TestCase):
    def setUp(self):
        # La migracion de backfill de Task 3 ya crea la empresa LOGINCO en la
        # base de datos de test antes de que corra setUp(), asi que se usa
        # get_or_create en vez de create() para evitar un IntegrityError.
        self.empresa, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )

    def test_formulario_muestra_las_empresas_activas(self):
        response = self.client.get(reverse('register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Loginco')
        self.assertContains(response, 'name="empresa"')

    def test_registro_asigna_la_empresa_elegida(self):
        response = self.client.post(reverse('register'), {
            'username': 'nuevo_empleado',
            'email': 'nuevo@example.com',
            'password': 'ClaveSegura123',
            'password_confirm': 'ClaveSegura123',
            'first_name': 'Nuevo',
            'last_name': 'Empleado',
            'codigo_empleado': 'NE001',
            'departamento': 'Ventas',
            'puesto': 'Vendedor',
            'empresa': self.empresa.id,
        })

        empleado = Empleado.objects.get(codigo_empleado='NE001')
        self.assertEqual(empleado.empresa, self.empresa)
        self.assertEqual(response.status_code, 302)

    def test_registro_sin_empresa_valida_no_crea_empleado(self):
        response = self.client.post(reverse('register'), {
            'username': 'sin_empresa',
            'email': 'sinempresa@example.com',
            'password': 'ClaveSegura123',
            'password_confirm': 'ClaveSegura123',
            'first_name': 'Sin',
            'last_name': 'Empresa',
            'codigo_empleado': 'SE002',
            'departamento': 'Ventas',
            'puesto': '',
            'empresa': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Empleado.objects.filter(codigo_empleado='SE002').exists())
