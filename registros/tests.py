import io
from datetime import date, datetime, time, timedelta
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from empleados.models import Empleado
from horarios.models import AsignacionHorario, TipoHorario
from organizacion.models import Empresa
from registros.models import RegistroAsistencia
from registros.services.turnos import obtener_registro_activo

MEXICO_TZ_TEST = ZoneInfo('America/Mexico_City')


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


def _dummy_foto():
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color='white').save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile('foto.jpg', buffer.read(), content_type='image/jpeg')


class MarcarAsistenciaTurnoNocturnoTests(TestCase):
    def setUp(self):
        self.empresa, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )
        user = User.objects.create_user(username='hotel_noc', password='x')
        self.empleado = Empleado.objects.create(
            user=user, codigo_empleado='HOT001', empresa=self.empresa
        )
        self.tipo_nocturno = TipoHorario.objects.create(
            nombre='Turno Nocturno Hotel', codigo='HOTNOC',
            hora_entrada=time(21, 0), hora_salida=time(7, 0),
            cruza_medianoche=True, tolerancia_minutos=10, tiene_comida=False
        )
        self.dia_1 = date(2026, 9, 10)
        self.dia_2 = date(2026, 9, 11)
        AsignacionHorario.objects.create(
            empleado=self.empleado, fecha=self.dia_1, tipo_horario=self.tipo_nocturno
        )
        AsignacionHorario.objects.create(
            empleado=self.empleado, fecha=self.dia_2, tipo_horario=self.tipo_nocturno
        )
        self.client = APIClient()

        # MediaStorage siempre usa S3Boto3Storage (DigitalOcean Spaces); en un
        # entorno de pruebas sin credenciales configuradas, save/exists/url
        # intentarían llamadas de red reales. Se reemplazan por versiones
        # inertes sólo para este test.
        save_patcher = patch(
            'checador.storage_backends.MediaStorage._save',
            side_effect=lambda name, content: name
        )
        exists_patcher = patch(
            'checador.storage_backends.MediaStorage.exists', return_value=False
        )
        url_patcher = patch(
            'checador.storage_backends.MediaStorage.url',
            return_value='https://example.com/fake.jpg'
        )
        for patcher in (save_patcher, exists_patcher, url_patcher):
            patcher.start()
            self.addCleanup(patcher.stop)

    @patch('registros.views.FacialRecognitionService.recognize_employee')
    @patch('registros.views.FacialRecognitionService.load_image_from_file')
    @patch('django.utils.timezone.now')
    def test_entrada_y_salida_de_turno_nocturno_quedan_en_un_solo_registro(
        self, mock_now, mock_load, mock_recognize
    ):
        mock_load.return_value = 'imagen-simulada'
        mock_recognize.return_value = (self.empleado, 98.5, 'ok')

        mock_now.return_value = datetime(2026, 9, 10, 21, 5, tzinfo=MEXICO_TZ_TEST)
        respuesta_entrada = self.client.post('/api/registros/marcar_entrada/', {
            'foto': _dummy_foto(), 'tipo': 'entrada'
        }, format='multipart')
        self.assertEqual(respuesta_entrada.status_code, 200, respuesta_entrada.content)

        mock_now.return_value = datetime(2026, 9, 11, 7, 10, tzinfo=MEXICO_TZ_TEST)
        respuesta_salida = self.client.post('/api/registros/marcar_salida/', {
            'foto': _dummy_foto(), 'tipo': 'salida'
        }, format='multipart')
        self.assertEqual(respuesta_salida.status_code, 200, respuesta_salida.content)

        self.assertEqual(RegistroAsistencia.objects.count(), 1)
        registro = RegistroAsistencia.objects.get()
        self.assertEqual(registro.fecha, self.dia_1)
        self.assertEqual(registro.hora_entrada, time(21, 5))
        self.assertEqual(registro.hora_salida, time(7, 10))
        self.assertAlmostEqual(registro.horas_trabajadas, 10 + 5 / 60, places=2)

    @patch('registros.views.FacialRecognitionService.recognize_employee')
    @patch('registros.views.FacialRecognitionService.load_image_from_file')
    @patch('django.utils.timezone.now')
    def test_no_permite_marcar_nueva_entrada_con_turno_nocturno_sin_cerrar(
        self, mock_now, mock_load, mock_recognize
    ):
        mock_load.return_value = 'imagen-simulada'
        mock_recognize.return_value = (self.empleado, 98.5, 'ok')

        mock_now.return_value = datetime(2026, 9, 10, 21, 5, tzinfo=MEXICO_TZ_TEST)
        self.client.post('/api/registros/marcar_entrada/', {
            'foto': _dummy_foto(), 'tipo': 'entrada'
        }, format='multipart')

        mock_now.return_value = datetime(2026, 9, 11, 8, 0, tzinfo=MEXICO_TZ_TEST)
        respuesta = self.client.post('/api/registros/marcar_entrada/', {
            'foto': _dummy_foto(), 'tipo': 'entrada'
        }, format='multipart')

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('turno nocturno sin cerrar', respuesta.json()['message'])
        self.assertEqual(RegistroAsistencia.objects.count(), 1)


class DetectarIncidenciasNocturnoTests(TestCase):
    def setUp(self):
        self.empresa, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )
        user = User.objects.create_user(username='noc_inc', password='x')
        self.empleado = Empleado.objects.create(
            user=user, codigo_empleado='NOC001', empresa=self.empresa
        )
        self.tipo_nocturno = TipoHorario.objects.create(
            nombre='Turno Nocturno Incidencias', codigo='NOCINC',
            hora_entrada=time(21, 0), hora_salida=time(7, 0),
            cruza_medianoche=True, tolerancia_minutos=10, tiene_comida=False
        )
        self.fecha_entrada = date(2026, 9, 10)
        AsignacionHorario.objects.create(
            empleado=self.empleado, fecha=self.fecha_entrada, tipo_horario=self.tipo_nocturno
        )
        self.registro = RegistroAsistencia.objects.create(
            empleado=self.empleado, fecha=self.fecha_entrada, hora_entrada=time(21, 5)
        )

    @patch('django.utils.timezone.now')
    def test_no_marca_incidencia_si_turno_nocturno_sigue_en_curso(self, mock_now):
        # Se ejecuta el comando a las 03:00 del día siguiente: la salida
        # esperada es hasta las 07:00 + 10 min de tolerancia.
        mock_now.return_value = datetime(2026, 9, 11, 3, 0, tzinfo=MEXICO_TZ_TEST)

        call_command('detectar_incidencias', fecha=str(self.fecha_entrada), stdout=StringIO())

        self.registro.refresh_from_db()
        self.assertEqual(self.registro.incidencia, 'ninguna')

    @patch('django.utils.timezone.now')
    def test_marca_sin_salida_si_ya_paso_la_hora_esperada_mas_tolerancia(self, mock_now):
        mock_now.return_value = datetime(2026, 9, 11, 7, 30, tzinfo=MEXICO_TZ_TEST)

        call_command('detectar_incidencias', fecha=str(self.fecha_entrada), stdout=StringIO())

        self.registro.refresh_from_db()
        self.assertEqual(self.registro.incidencia, 'sin_salida')
