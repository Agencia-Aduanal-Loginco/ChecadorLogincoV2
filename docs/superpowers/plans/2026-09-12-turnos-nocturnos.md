# Turnos Nocturnos (cruzan medianoche) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir capturar y marcar (entrada/salida) turnos de hotel que inician en la noche y terminan la mañana siguiente (ej. 21:00 → 07:00), quedando en un solo `RegistroAsistencia` por turno.

**Architecture:** Se agrega un campo explícito `cruza_medianoche` a `TipoHorario` que habilita horas invertidas (`hora_salida <= hora_entrada`) sólo cuando el turno realmente cruza medianoche. Un nuevo helper `obtener_registro_activo` decide, en cada marcado, si debe operar sobre el registro de hoy o sobre un turno nocturno de ayer que sigue abierto. Se corrigen dos bugs colaterales: comparación de horario de comida que también cruza medianoche, y falsos positivos de "sin_salida" en el detector de incidencias mientras el turno nocturno sigue en curso.

**Tech Stack:** Django 6.0, Django REST Framework, `django.test.TestCase`, `rest_framework.test.APIClient`, `unittest.mock`.

## Global Constraints

- Alcance limitado a `TipoHorario` / `AsignacionHorario`. El modelo semanal `Horario` NO recibe el campo `cruza_medianoche` (spec, sección "Decisión de diseño"). El fix de `esta_en_horario_comida` sí aplica a ambos modelos porque es un bug independiente de rango horario.
- Un turno nocturno se representa como **un solo** `RegistroAsistencia`, con `fecha` = el día en que inició el turno (spec, sección "Decisión de diseño").
- Fuera de alcance en este cambio: dashboard/reportes de "hoy" en `checador/views.py` (spec, sección 5).
- Zona horaria: todas las comparaciones de "ahora" usan `America/Mexico_City` (`MEXICO_TZ`), igual que el resto del código existente.
- Cada tarea sigue TDD: escribir la prueba, verla fallar, implementar lo mínimo, verla pasar, commit.

---

### Task 1: Campo `cruza_medianoche` en `TipoHorario` + validación

**Files:**
- Modify: `horarios/models.py:6-55` (clase `TipoHorario`)
- Modify: `horarios/admin.py:12-18` (fieldset "Horario" de `TipoHorarioAdmin`)
- Test: `horarios/tests.py`
- Create (autogenerado): `horarios/migrations/0004_tipohorario_cruza_medianoche.py`

**Interfaces:**
- Produces: `TipoHorario.cruza_medianoche` (`BooleanField`, default `False`). Usado por Task 2 (serializer), Task 5 (`obtener_registro_activo`) y Task 7 (`detectar_incidencias`) vía `getattr(horario_info['objeto'], 'cruza_medianoche', False)`.

- [ ] **Step 1: Escribir las pruebas que fallan**

Agrega al final de `horarios/tests.py`:

```python
from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from horarios.models import TipoHorario


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
```

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

Run: `python manage.py test horarios.tests.TipoHorarioCruzaMedianocheTests -v 2`
Expected: FAIL — `TypeError: TipoHorario() got unexpected keyword arguments: 'cruza_medianoche'` (el campo no existe todavía).

- [ ] **Step 3: Agregar el campo y actualizar `clean()`**

En `horarios/models.py`, dentro de la clase `TipoHorario` (после la línea `hora_salida = models.TimeField(verbose_name='Hora de Salida')`, línea 19), agrega:

```python
    cruza_medianoche = models.BooleanField(
        default=False,
        verbose_name='Cruza medianoche',
        help_text='Activar si la salida ocurre al día siguiente (ej. turno 21:00 - 7:00)'
    )
```

Reemplaza el método `clean()` de `TipoHorario` (líneas 47-49):

```python
    def clean(self):
        if self.hora_salida and self.hora_entrada and self.hora_salida <= self.hora_entrada:
            raise ValidationError('La hora de salida debe ser posterior a la hora de entrada.')
```

por:

```python
    def clean(self):
        if not self.hora_salida or not self.hora_entrada:
            return
        cruza = self.hora_salida <= self.hora_entrada
        if cruza and not self.cruza_medianoche:
            raise ValidationError(
                'La hora de salida debe ser posterior a la hora de entrada. '
                'Si el turno termina al día siguiente, marca "Cruza medianoche".'
            )
        if not cruza and self.cruza_medianoche:
            raise ValidationError(
                'Si el turno no cruza medianoche, la hora de salida debe ser posterior '
                'a la hora de entrada y debes desmarcar "Cruza medianoche".'
            )
```

- [ ] **Step 4: Agregar el campo al admin**

En `horarios/admin.py`, dentro de `TipoHorarioAdmin.fieldsets`, cambia:

```python
        ('Horario', {
            'fields': ('hora_entrada', 'hora_salida', 'tolerancia_minutos')
        }),
```

por:

```python
        ('Horario', {
            'fields': ('hora_entrada', 'hora_salida', 'cruza_medianoche', 'tolerancia_minutos')
        }),
```

- [ ] **Step 5: Generar y aplicar la migración**

Run: `python manage.py makemigrations horarios`
Expected: `Migrations for 'horarios': horarios/migrations/0004_tipohorario_cruza_medianoche.py - Add field cruza_medianoche to tipohorario`

Run: `python manage.py migrate horarios`
Expected: `Applying horarios.0004_tipohorario_cruza_medianoche... OK`

- [ ] **Step 6: Correr las pruebas y verificar que pasan**

Run: `python manage.py test horarios.tests.TipoHorarioCruzaMedianocheTests -v 2`
Expected: PASS (3 tests)

- [ ] **Step 7: Commit**

```bash
git add horarios/models.py horarios/admin.py horarios/tests.py horarios/migrations/0004_tipohorario_cruza_medianoche.py
git commit -m "$(cat <<'EOF'
Agrega cruza_medianoche a TipoHorario para soportar turnos nocturnos

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MYzcLBaUJDerJDQQVJqEiL
EOF
)"
```

---

### Task 2: Validación del campo en `TipoHorarioSerializer`

**Files:**
- Modify: `horarios/serializers.py:6-15` (clase `TipoHorarioSerializer`)
- Test: `horarios/tests.py`

**Interfaces:**
- Consumes: `TipoHorario.cruza_medianoche` (Task 1).
- Produces: `TipoHorarioSerializer` acepta/rechaza `cruza_medianoche` igual que `TipoHorario.clean()`, incluyendo actualizaciones parciales (`PATCH`).

- [ ] **Step 1: Escribir las pruebas que fallan**

Agrega al final de `horarios/tests.py`:

```python
from horarios.serializers import TipoHorarioSerializer


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
```

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

Run: `python manage.py test horarios.tests.TipoHorarioSerializerCruzaMedianocheTests -v 2`
Expected: FAIL — `test_serializer_rechaza_cruza_medianoche_true_sin_horas_invertidas` y `test_serializer_rechaza_horas_invertidas_sin_marcar_cruza_medianoche` fallan porque el serializer todavía no valida `cruza_medianoche` (ambos casos se aceptan indebidamente); el primer test puede pasar por accidente pero lo dejamos igual para fijar el comportamiento completo.

- [ ] **Step 3: Actualizar `TipoHorarioSerializer`**

En `horarios/serializers.py`, reemplaza la clase completa `TipoHorarioSerializer` (líneas 6-15):

```python
class TipoHorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoHorario
        fields = (
            'id', 'nombre', 'codigo', 'descripcion', 'color',
            'hora_entrada', 'hora_salida', 'tolerancia_minutos',
            'tiene_comida', 'hora_inicio_comida', 'hora_fin_comida',
            'activo', 'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')
```

por:

```python
class TipoHorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoHorario
        fields = (
            'id', 'nombre', 'codigo', 'descripcion', 'color',
            'hora_entrada', 'hora_salida', 'cruza_medianoche', 'tolerancia_minutos',
            'tiene_comida', 'hora_inicio_comida', 'hora_fin_comida',
            'activo', 'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')

    def validate(self, attrs):
        hora_entrada = attrs.get('hora_entrada', getattr(self.instance, 'hora_entrada', None))
        hora_salida = attrs.get('hora_salida', getattr(self.instance, 'hora_salida', None))
        cruza_medianoche = attrs.get(
            'cruza_medianoche', getattr(self.instance, 'cruza_medianoche', False)
        )

        if hora_entrada and hora_salida:
            cruza = hora_salida <= hora_entrada
            if cruza and not cruza_medianoche:
                raise serializers.ValidationError({
                    'hora_salida': (
                        'La hora de salida debe ser posterior a la hora de entrada, '
                        'o activa "cruza_medianoche" si el turno termina al día siguiente.'
                    )
                })
            if not cruza and cruza_medianoche:
                raise serializers.ValidationError({
                    'cruza_medianoche': (
                        'El turno no cruza medianoche según las horas capturadas; '
                        'desactiva esta opción.'
                    )
                })
        return attrs
```

- [ ] **Step 4: Correr las pruebas y verificar que pasan**

Run: `python manage.py test horarios.tests.TipoHorarioSerializerCruzaMedianocheTests -v 2`
Expected: PASS (3 tests)

- [ ] **Step 5: Correr toda la suite de `horarios` como regresión**

Run: `python manage.py test horarios`
Expected: PASS (todas las pruebas, incluyendo las de Task 1)

- [ ] **Step 6: Commit**

```bash
git add horarios/serializers.py horarios/tests.py
git commit -m "$(cat <<'EOF'
Valida cruza_medianoche en TipoHorarioSerializer

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MYzcLBaUJDerJDQQVJqEiL
EOF
)"
```

---

### Task 3: `esta_en_horario_comida` soporta comida que cruza medianoche

**Files:**
- Modify: `horarios/models.py` (método `esta_en_horario_comida` en `TipoHorario`, líneas 51-54, y en `Horario`, líneas 169-173)
- Test: `horarios/tests.py`

**Interfaces:**
- Produces: `TipoHorario.esta_en_horario_comida(hora_actual)` y `Horario.esta_en_horario_comida(hora_actual)` devuelven `True` cuando `hora_actual` cae dentro de un rango de comida que envuelve la medianoche (`hora_inicio_comida > hora_fin_comida`).

- [ ] **Step 1: Escribir las pruebas que fallan**

Agrega al final de `horarios/tests.py`:

```python
from django.contrib.auth.models import User

from empleados.models import Empleado
from horarios.models import Horario
from organizacion.models import Empresa


class EstaEnHorarioComidaWraparoundTests(TestCase):
    def test_tipohorario_comida_que_cruza_medianoche_dentro_del_rango(self):
        tipo = TipoHorario.objects.create(
            nombre='Turno Nocturno Comida', codigo='NOCCOM',
            hora_entrada=time(21, 0), hora_salida=time(7, 0), cruza_medianoche=True,
            tiene_comida=True, hora_inicio_comida=time(1, 0), hora_fin_comida=time(1, 30)
        )
        self.assertTrue(tipo.esta_en_horario_comida(time(1, 15)))

    def test_tipohorario_comida_que_cruza_medianoche_fuera_del_rango(self):
        tipo = TipoHorario.objects.create(
            nombre='Turno Nocturno Comida 2', codigo='NOCCOM2',
            hora_entrada=time(21, 0), hora_salida=time(7, 0), cruza_medianoche=True,
            tiene_comida=True, hora_inicio_comida=time(1, 0), hora_fin_comida=time(1, 30)
        )
        self.assertFalse(tipo.esta_en_horario_comida(time(12, 0)))


class HorarioComidaWraparoundTests(TestCase):
    def setUp(self):
        self.empresa, _ = Empresa.objects.get_or_create(
            codigo='LOGINCO', defaults={'nombre': 'Loginco'}
        )
        user = User.objects.create_user(username='horario_comida', password='x')
        self.empleado = Empleado.objects.create(
            user=user, codigo_empleado='HC001', empresa=self.empresa
        )

    def test_horario_comida_que_cruza_medianoche_dentro_del_rango(self):
        horario = Horario.objects.create(
            empleado=self.empleado, dia_semana=1,
            hora_entrada=time(8, 0), hora_salida=time(17, 0),
            tiene_comida=True, hora_inicio_comida=time(23, 30), hora_fin_comida=time(0, 30)
        )
        self.assertTrue(horario.esta_en_horario_comida(time(23, 45)))
        self.assertTrue(horario.esta_en_horario_comida(time(0, 15)))

    def test_horario_comida_que_cruza_medianoche_fuera_del_rango(self):
        horario = Horario.objects.create(
            empleado=self.empleado, dia_semana=1,
            hora_entrada=time(8, 0), hora_salida=time(17, 0),
            tiene_comida=True, hora_inicio_comida=time(23, 30), hora_fin_comida=time(0, 30)
        )
        self.assertFalse(horario.esta_en_horario_comida(time(12, 0)))
```

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

Run: `python manage.py test horarios.tests.EstaEnHorarioComidaWraparoundTests horarios.tests.HorarioComidaWraparoundTests -v 2`
Expected: FAIL en los 3 casos que cruzan medianoche (`test_tipohorario_comida_que_cruza_medianoche_dentro_del_rango`, y los dos de `HorarioComidaWraparoundTests`) porque la comparación actual `inicio <= actual <= fin` es imposible cuando `inicio > fin`.

- [ ] **Step 3: Corregir `esta_en_horario_comida` en `TipoHorario`**

Reemplaza en `horarios/models.py` (líneas 51-54):

```python
    def esta_en_horario_comida(self, hora_actual):
        if not self.tiene_comida or not self.hora_inicio_comida or not self.hora_fin_comida:
            return False
        return self.hora_inicio_comida <= hora_actual <= self.hora_fin_comida
```

por:

```python
    def esta_en_horario_comida(self, hora_actual):
        if not self.tiene_comida or not self.hora_inicio_comida or not self.hora_fin_comida:
            return False
        if self.hora_inicio_comida <= self.hora_fin_comida:
            return self.hora_inicio_comida <= hora_actual <= self.hora_fin_comida
        # La comida cruza medianoche (ej. 01:00 - 01:30 en un turno nocturno)
        return hora_actual >= self.hora_inicio_comida or hora_actual <= self.hora_fin_comida
```

- [ ] **Step 4: Aplicar el mismo fix en `Horario`**

Reemplaza en `horarios/models.py` (líneas 169-173):

```python
    def esta_en_horario_comida(self, hora_actual):
        """Verifica si la hora actual está dentro del horario de comida"""
        if not self.tiene_comida or not self.hora_inicio_comida or not self.hora_fin_comida:
            return False
        return self.hora_inicio_comida <= hora_actual <= self.hora_fin_comida
```

por:

```python
    def esta_en_horario_comida(self, hora_actual):
        """Verifica si la hora actual está dentro del horario de comida"""
        if not self.tiene_comida or not self.hora_inicio_comida or not self.hora_fin_comida:
            return False
        if self.hora_inicio_comida <= self.hora_fin_comida:
            return self.hora_inicio_comida <= hora_actual <= self.hora_fin_comida
        # La comida cruza medianoche
        return hora_actual >= self.hora_inicio_comida or hora_actual <= self.hora_fin_comida
```

- [ ] **Step 5: Correr las pruebas y verificar que pasan**

Run: `python manage.py test horarios.tests.EstaEnHorarioComidaWraparoundTests horarios.tests.HorarioComidaWraparoundTests -v 2`
Expected: PASS (4 tests)

- [ ] **Step 6: Correr toda la suite de `horarios` como regresión**

Run: `python manage.py test horarios`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add horarios/models.py horarios/tests.py
git commit -m "$(cat <<'EOF'
Corrige esta_en_horario_comida para comida que cruza medianoche

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MYzcLBaUJDerJDQQVJqEiL
EOF
)"
```

---

### Task 4: Helper `obtener_registro_activo`

**Files:**
- Create: `registros/services/turnos.py`
- Modify: `registros/services/__init__.py`
- Test: `registros/tests.py`

**Interfaces:**
- Consumes: `RegistroAsistencia` (registros/models.py), `horarios.services.obtener_horario_del_dia(empleado, fecha)` (ya existe, retorna `dict` con clave `'objeto'`), `TipoHorario.cruza_medianoche` (Task 1).
- Produces: `obtener_registro_activo(empleado, fecha_hoy) -> (registro: RegistroAsistencia | None, es_turno_nocturno_pendiente: bool)`. Usado por Task 5 (`registros/views.py`).

- [ ] **Step 1: Escribir las pruebas que fallan**

Agrega al final de `registros/tests.py`:

```python
from datetime import date, time, timedelta

from django.contrib.auth.models import User

from empleados.models import Empleado
from horarios.models import AsignacionHorario, TipoHorario
from organizacion.models import Empresa
from registros.models import RegistroAsistencia
from registros.services.turnos import obtener_registro_activo


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
```

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

Run: `python manage.py test registros.tests.ObtenerRegistroActivoTests -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'registros.services.turnos'`

- [ ] **Step 3: Crear `registros/services/turnos.py`**

```python
from datetime import timedelta

from horarios.services import obtener_horario_del_dia

from ..models import RegistroAsistencia


def obtener_registro_activo(empleado, fecha_hoy):
    """
    Resuelve sobre qué RegistroAsistencia debe operar un marcado de asistencia.

    Si el empleado tiene un turno nocturno del día anterior que sigue abierto
    (con hora_entrada pero sin hora_salida, y el horario asignado ese día
    tiene cruza_medianoche=True), se retorna ese registro para que la salida
    (o la comida) se marque ahí en vez de crear un registro nuevo para hoy.

    Retorna una tupla (registro, es_turno_nocturno_pendiente):
    - registro: la instancia de RegistroAsistencia encontrada, o None si no
      existe ninguna para hoy ni un turno nocturno pendiente de ayer (el
      llamador debe crear una nueva para fecha_hoy en ese caso).
    - es_turno_nocturno_pendiente: True si el registro retornado es el de
      ayer y corresponde a un turno nocturno todavía sin hora_salida.
    """
    fecha_ayer = fecha_hoy - timedelta(days=1)
    registro_ayer = RegistroAsistencia.objects.filter(
        empleado=empleado, fecha=fecha_ayer
    ).first()

    if registro_ayer and registro_ayer.hora_entrada and not registro_ayer.hora_salida:
        horario_ayer = obtener_horario_del_dia(empleado, fecha_ayer)
        if horario_ayer and getattr(horario_ayer['objeto'], 'cruza_medianoche', False):
            return registro_ayer, True

    registro_hoy = RegistroAsistencia.objects.filter(
        empleado=empleado, fecha=fecha_hoy
    ).first()
    return registro_hoy, False
```

- [ ] **Step 4: Exportarlo desde el paquete de servicios**

Reemplaza `registros/services/__init__.py`:

```python
from .facial_recognition import FacialRecognitionService
from .turnos import obtener_registro_activo

__all__ = ['FacialRecognitionService', 'obtener_registro_activo']
```

- [ ] **Step 5: Correr las pruebas y verificar que pasan**

Run: `python manage.py test registros.tests.ObtenerRegistroActivoTests -v 2`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add registros/services/turnos.py registros/services/__init__.py registros/tests.py
git commit -m "$(cat <<'EOF'
Agrega obtener_registro_activo para resolver turnos nocturnos abiertos

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MYzcLBaUJDerJDQQVJqEiL
EOF
)"
```

---

### Task 5: Usar `obtener_registro_activo` en `_marcar_asistencia` y `verificar_rostro`

**Files:**
- Modify: `registros/views.py:10` (import), `registros/views.py:93-149` (`verificar_rostro`), `registros/views.py:177-291` (`_marcar_asistencia`)
- Test: `registros/tests.py`

**Interfaces:**
- Consumes: `obtener_registro_activo(empleado, fecha_hoy)` (Task 4).
- Produces: comportamiento end-to-end de `/api/registros/marcar_entrada/` y `/api/registros/marcar_salida/` para turnos nocturnos (usado en pruebas de este task, no consumido por tasks posteriores).

- [ ] **Step 1: Escribir las pruebas que fallan**

Agrega al final de `registros/tests.py`:

```python
import io
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

MEXICO_TZ_TEST = ZoneInfo('America/Mexico_City')


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
```

Nota: este test reutiliza `TestCase`, `date`, `time`, `User`, `Empleado`, `Empresa`, `TipoHorario`, `AsignacionHorario`, `RegistroAsistencia` ya importados por los tasks anteriores en `registros/tests.py`. Si alguno falta, agrega el import correspondiente junto a los existentes al inicio del archivo.

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

Run: `python manage.py test registros.tests.MarcarAsistenciaTurnoNocturnoTests -v 2`
Expected: FAIL — `test_entrada_y_salida_de_turno_nocturno_quedan_en_un_solo_registro` falla con `RegistroAsistencia.objects.count()` igual a `2` (o con la salida devolviendo 400 "No hay entrada registrada para marcar salida"), y `test_no_permite_marcar_nueva_entrada_con_turno_nocturno_sin_cerrar` falla porque hoy no bloquea la segunda entrada.

- [ ] **Step 3: Agregar el import del helper**

En `registros/views.py`, después de la línea 10 (`from .services import FacialRecognitionService`), agrega:

```python
from .services.turnos import obtener_registro_activo
```

- [ ] **Step 4: Actualizar `verificar_rostro`**

Reemplaza en `registros/views.py` (líneas 98-106):

```python
        # Obtener o crear registro del día
        registro, created = RegistroAsistencia.objects.get_or_create(
            empleado=empleado,
            fecha=hoy
        )
        
        # Obtener horario del dia usando el nuevo servicio
        from horarios.services import obtener_horario_del_dia
        horario_data = obtener_horario_del_dia(empleado, hoy)
```

por:

```python
        # Obtener el registro activo: el de hoy, o el de ayer si hay un
        # turno nocturno todavía sin cerrar
        registro, _es_nocturno_pendiente = obtener_registro_activo(empleado, hoy)
        if registro is None:
            registro = RegistroAsistencia.objects.create(empleado=empleado, fecha=hoy)

        # Obtener horario del dia usando el nuevo servicio
        from horarios.services import obtener_horario_del_dia
        horario_data = obtener_horario_del_dia(empleado, registro.fecha)
```

- [ ] **Step 5: Actualizar `_marcar_asistencia`**

Reemplaza en `registros/views.py` (líneas 203-216):

```python
        # Obtener o crear registro del día (usando hora de México)
        ahora_mexico = timezone.now().astimezone(MEXICO_TZ)
        hoy = ahora_mexico.date()
        registro, created = RegistroAsistencia.objects.get_or_create(
            empleado=empleado,
            fecha=hoy,
            defaults={
                'reconocimiento_facial': True,
                'confianza_reconocimiento': confianza,
                'latitud': latitud,
                'longitud': longitud,
                'ubicacion': ubicacion
            }
        )
```

por:

```python
        # Obtener el registro activo (usando hora de México): el de hoy,
        # o el de ayer si hay un turno nocturno todavía sin cerrar
        ahora_mexico = timezone.now().astimezone(MEXICO_TZ)
        hoy = ahora_mexico.date()
        registro, es_nocturno_pendiente = obtener_registro_activo(empleado, hoy)

        if tipo == 'entrada' and es_nocturno_pendiente:
            return Response({
                'success': False,
                'message': (
                    f'Tienes un turno nocturno sin cerrar del {registro.fecha}, '
                    'marca tu salida primero'
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        if registro is None:
            registro = RegistroAsistencia.objects.create(
                empleado=empleado,
                fecha=hoy,
                reconocimiento_facial=True,
                confianza_reconocimiento=confianza,
                latitud=latitud,
                longitud=longitud,
                ubicacion=ubicacion
            )
```

El resto del método (desde `ahora = ahora_mexico.time()` hasta el final) no cambia.

- [ ] **Step 6: Correr las pruebas y verificar que pasan**

Run: `python manage.py test registros.tests.MarcarAsistenciaTurnoNocturnoTests -v 2`
Expected: PASS (2 tests)

- [ ] **Step 7: Correr toda la suite de `registros` como regresión**

Run: `python manage.py test registros`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add registros/views.py registros/tests.py
git commit -m "$(cat <<'EOF'
Resuelve el registro activo al marcar entrada/salida de turnos nocturnos

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MYzcLBaUJDerJDQQVJqEiL
EOF
)"
```

---

### Task 6: `detectar_incidencias` no marca falso "sin_salida" en turnos nocturnos en curso

**Files:**
- Modify: `registros/management/commands/detectar_incidencias.py`
- Test: `registros/tests.py`

**Interfaces:**
- Consumes: `horarios.services.obtener_horario_del_dia`, `TipoHorario.cruza_medianoche` (Task 1).
- Produces: comportamiento del comando `python manage.py detectar_incidencias` (usado en pruebas de este task; no consumido por otros módulos).

- [ ] **Step 1: Escribir las pruebas que fallan**

Agrega al final de `registros/tests.py`:

```python
from io import StringIO

from django.core.management import call_command


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
```

Nota: `patch`, `datetime` y `MEXICO_TZ_TEST` ya quedaron importados/definidos por el bloque de pruebas de Task 5; sólo `StringIO` y `call_command` son imports nuevos en este bloque.

- [ ] **Step 2: Correr las pruebas y verificar que fallan**

Run: `python manage.py test registros.tests.DetectarIncidenciasNocturnoTests -v 2`
Expected: FAIL en `test_no_marca_incidencia_si_turno_nocturno_sigue_en_curso` — hoy el comando marca `sin_salida` sin importar la hora, así que la incidencia queda en `'sin_salida'` en vez de `'ninguna'`.

- [ ] **Step 3: Actualizar el comando**

Reemplaza el contenido completo de `registros/management/commands/detectar_incidencias.py`:

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from horarios.services import obtener_horario_del_dia
from registros.models import RegistroAsistencia

MEXICO_TZ = ZoneInfo('America/Mexico_City')


class Command(BaseCommand):
    help = 'Detecta y marca incidencias en registros de asistencia del día anterior'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha específica a revisar (YYYY-MM-DD). Por defecto: día anterior',
        )

    def handle(self, *args, **options):
        ahora_mexico = timezone.now().astimezone(MEXICO_TZ)

        if options['fecha']:
            fecha_revisar = datetime.strptime(options['fecha'], '%Y-%m-%d').date()
        else:
            fecha_revisar = (ahora_mexico - timedelta(days=1)).date()

        self.stdout.write(f"Revisando registros del día: {fecha_revisar}")

        registros = RegistroAsistencia.objects.filter(fecha=fecha_revisar)

        total_registros = registros.count()
        registros_con_incidencia = 0
        registros_completos = 0
        registros_nocturnos_en_curso = 0

        for registro in registros:
            if self._es_turno_nocturno_en_curso(registro, ahora_mexico):
                registros_nocturnos_en_curso += 1
                self.stdout.write(
                    f"  🌙 {registro.empleado.codigo_empleado}: turno nocturno aún en "
                    "curso, se revisará más tarde"
                )
                continue

            registro.calcular_incidencias()
            registro.save()

            if registro.incidencia != 'ninguna':
                registros_con_incidencia += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  {registro.empleado.codigo_empleado} - {registro.empleado.nombre_completo}: "
                        f"{registro.get_incidencia_display()} - {registro.descripcion_incidencia}"
                    )
                )
            else:
                registros_completos += 1

        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"Total de registros revisados: {total_registros}")
        self.stdout.write(self.style.SUCCESS(f"✓ Registros completos: {registros_completos}"))

        if registros_nocturnos_en_curso:
            self.stdout.write(f"🌙 Turnos nocturnos aún en curso: {registros_nocturnos_en_curso}")

        if registros_con_incidencia > 0:
            self.stdout.write(self.style.ERROR(f"✗ Registros con incidencia: {registros_con_incidencia}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ No se encontraron incidencias"))

        self.stdout.write("="*60)
        self.stdout.write(self.style.SUCCESS(f"\n✓ Proceso completado exitosamente"))

    def _es_turno_nocturno_en_curso(self, registro, ahora_mexico):
        """True si el registro es un turno nocturno que aún no debería haber cerrado."""
        if not registro.hora_entrada or registro.hora_salida:
            return False

        horario_info = obtener_horario_del_dia(registro.empleado, registro.fecha)
        if not horario_info or not getattr(horario_info['objeto'], 'cruza_medianoche', False):
            return False

        hora_salida_esperada = datetime.combine(
            registro.fecha + timedelta(days=1),
            horario_info['hora_salida'],
            tzinfo=MEXICO_TZ
        )
        limite = hora_salida_esperada + timedelta(minutes=horario_info['tolerancia_minutos'])
        return ahora_mexico < limite
```

- [ ] **Step 4: Correr las pruebas y verificar que pasan**

Run: `python manage.py test registros.tests.DetectarIncidenciasNocturnoTests -v 2`
Expected: PASS (2 tests)

- [ ] **Step 5: Correr toda la suite de `registros` como regresión final**

Run: `python manage.py test registros`
Expected: PASS

- [ ] **Step 6: Correr toda la suite del proyecto como regresión final**

Run: `python manage.py test`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add registros/management/commands/detectar_incidencias.py registros/tests.py
git commit -m "$(cat <<'EOF'
Evita falso sin_salida en detectar_incidencias para turnos nocturnos en curso

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01MYzcLBaUJDerJDQQVJqEiL
EOF
)"
```
