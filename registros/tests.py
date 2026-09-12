from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from empleados.models import Empleado
from horarios.models import AsignacionHorario, TipoHorario
from organizacion.models import Empresa
from registros.models import RegistroAsistencia
from registros.services.turnos import obtener_registro_activo


class FacialRecognitionComidaTemplateTests(TestCase):
    """Verifica la estructura de botones dinámicos en /checador/."""

    def test_contenedor_de_acciones_envuelve_los_cuatro_botones(self):
        response = self.client.get(reverse('facial_recognition_comida'))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        inicio_contenedor = content.index('id="accionesContainer"')
        fin_contenedor = content.index('<!-- Botón para verificar de nuevo -->')

        self.assertGreater(fin_contenedor, inicio_contenedor)
        bloque = content[inicio_contenedor:fin_contenedor]

        self.assertIn('id="btnEntrada"', bloque)
        self.assertIn('id="btnSalidaComida"', bloque)
        self.assertIn('id="btnEntradaComida"', bloque)
        self.assertIn('id="btnSalida"', bloque)

    def test_mensaje_dia_completo_existe_y_oculto_por_defecto(self):
        response = self.client.get(reverse('facial_recognition_comida'))
        content = response.content.decode()

        self.assertIn('id="diaCompletoMsg" class="hidden', content)

    def test_script_oculta_botones_no_disponibles(self):
        response = self.client.get(reverse('facial_recognition_comida'))
        content = response.content.decode()

        self.assertIn("classList.toggle('hidden', !activo)", content)
        self.assertIn(
            "classList.toggle('hidden', disponibles.length === 0)", content
        )
        self.assertIn(
            "classList.toggle('hidden', disponibles.length > 0)", content
        )


class ObtenerRegistroActivoTests(TestCase):
    def setUp(self):
        self.empresa, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )
        user = User.objects.create_user(username='turno_noc', password='x')
        self.empleado = Empleado.objects.create(
            user=user, codigo_empleado='TN001', empresa=self.empresa
        )
        self.hoy = date(2026, 9, 11)
        self.ayer = self.hoy - timedelta(days=1)

    def test_sin_registros_retorna_none(self):
        registro, pendiente = obtener_registro_activo(self.empleado, self.hoy)
        self.assertIsNone(registro)
        self.assertFalse(pendiente)

    def test_turno_nocturno_de_ayer_abierto_se_retorna_como_pendiente(self):
        tipo_nocturno = TipoHorario.objects.create(
            nombre='Nocturno', codigo='NOCACT',
            hora_entrada=time(21, 0), hora_salida=time(7, 0), cruza_medianoche=True
        )
        AsignacionHorario.objects.create(
            empleado=self.empleado, fecha=self.ayer, tipo_horario=tipo_nocturno
        )
        registro_ayer = RegistroAsistencia.objects.create(
            empleado=self.empleado, fecha=self.ayer, hora_entrada=time(21, 5)
        )

        registro, pendiente = obtener_registro_activo(self.empleado, self.hoy)

        self.assertEqual(registro.pk, registro_ayer.pk)
        self.assertTrue(pendiente)

    def test_turno_de_ayer_ya_cerrado_no_se_considera_pendiente(self):
        tipo_nocturno = TipoHorario.objects.create(
            nombre='Nocturno2', codigo='NOCACT2',
            hora_entrada=time(21, 0), hora_salida=time(7, 0), cruza_medianoche=True
        )
        AsignacionHorario.objects.create(
            empleado=self.empleado, fecha=self.ayer, tipo_horario=tipo_nocturno
        )
        RegistroAsistencia.objects.create(
            empleado=self.empleado, fecha=self.ayer,
            hora_entrada=time(21, 5), hora_salida=time(7, 2)
        )

        registro, pendiente = obtener_registro_activo(self.empleado, self.hoy)

        self.assertIsNone(registro)
        self.assertFalse(pendiente)

    def test_registro_de_ayer_abierto_sin_horario_nocturno_no_se_considera_pendiente(self):
        tipo_diurno = TipoHorario.objects.create(
            nombre='Diurno', codigo='DIUACT',
            hora_entrada=time(8, 0), hora_salida=time(17, 0), cruza_medianoche=False
        )
        AsignacionHorario.objects.create(
            empleado=self.empleado, fecha=self.ayer, tipo_horario=tipo_diurno
        )
        RegistroAsistencia.objects.create(
            empleado=self.empleado, fecha=self.ayer, hora_entrada=time(8, 5)
        )

        registro, pendiente = obtener_registro_activo(self.empleado, self.hoy)

        self.assertIsNone(registro)
        self.assertFalse(pendiente)
