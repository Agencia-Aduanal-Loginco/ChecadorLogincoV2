from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from horarios.models import TipoHorario
from horarios.serializers import TipoHorarioSerializer


class TipoHorarioCruzaMedianocheTests(TestCase):
    def test_turno_nocturno_valido_se_guarda_sin_error(self):
        tipo = TipoHorario(
            nombre='Turno Nocturno', codigo='NOC',
            hora_entrada=time(21, 0), hora_salida=time(7, 0),
            cruza_medianoche=True
        )
        tipo.full_clean()  # no debe lanzar excepción
        tipo.save()
        self.assertTrue(TipoHorario.objects.filter(codigo='NOC').exists())

    def test_cruza_medianoche_true_pero_salida_mayor_a_entrada_falla(self):
        tipo = TipoHorario(
            nombre='Turno Invalido', codigo='INV',
            hora_entrada=time(8, 0), hora_salida=time(16, 0),
            cruza_medianoche=True
        )
        with self.assertRaises(ValidationError):
            tipo.full_clean()

    def test_cruza_medianoche_false_y_salida_menor_a_entrada_sigue_fallando(self):
        tipo = TipoHorario(
            nombre='Turno Diurno Invertido', codigo='DIU',
            hora_entrada=time(16, 0), hora_salida=time(8, 0),
            cruza_medianoche=False
        )
        with self.assertRaises(ValidationError):
            tipo.full_clean()


class TipoHorarioSerializerCruzaMedianocheTests(TestCase):
    def test_serializer_acepta_turno_nocturno_valido(self):
        data = {
            'nombre': 'Turno Nocturno API', 'codigo': 'NOCAPI',
            'hora_entrada': '21:00:00', 'hora_salida': '07:00:00',
            'cruza_medianoche': True
        }
        serializer = TipoHorarioSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_rechaza_cruza_medianoche_true_sin_horas_invertidas(self):
        data = {
            'nombre': 'Turno Invalido API', 'codigo': 'INVAPI',
            'hora_entrada': '08:00:00', 'hora_salida': '16:00:00',
            'cruza_medianoche': True
        }
        serializer = TipoHorarioSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('cruza_medianoche', serializer.errors)

    def test_serializer_rechaza_horas_invertidas_sin_marcar_cruza_medianoche(self):
        data = {
            'nombre': 'Turno Diurno Invertido API', 'codigo': 'DIUAPI',
            'hora_entrada': '16:00:00', 'hora_salida': '08:00:00',
            'cruza_medianoche': False
        }
        serializer = TipoHorarioSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('hora_salida', serializer.errors)
