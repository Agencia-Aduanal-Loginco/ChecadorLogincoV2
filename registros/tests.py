from django.test import TestCase
from django.urls import reverse


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
