# Turnos nocturnos (cruzan medianoche) — Diseño

## Contexto

Una de las empresas del sistema es un hotel, con horarios que operan los 7 días de la
semana y algunos turnos que inician en la noche (ej. 21:00) y terminan la mañana
siguiente (ej. 7:00). El hotel define sus horarios con `TipoHorario` +
`AsignacionHorario` (plantilla reutilizable asignada por fecha a cada empleado), no con
el modelo semanal `Horario`.

Hoy el sistema no soporta esto por dos motivos:

1. **Validación bloqueante.** `TipoHorario.clean()` (horarios/models.py) y los
   serializers `HorarioSerializer`/`HorarioCreateUpdateSerializer` (horarios/serializers.py)
   rechazan cualquier horario donde `hora_salida <= hora_entrada`. Un turno 21:00→7:00
   no se puede guardar.
2. **Resolución de registro por fecha del reloj.** `_marcar_asistencia`
   (registros/views.py) hace `get_or_create(empleado, fecha=hoy)` usando la fecha
   *del momento del ponche*. Si la entrada se marca el día D a las 21:00 (fecha=D) y la
   salida se marca el día D+1 a las 7:00, el sistema busca/crea un registro con
   `fecha=D+1` sin `hora_entrada`, y `marcar_salida` falla con "No hay entrada
   registrada para marcar salida". `calcular_horas_trabajadas` ya sabe sumar un día si
   `salida < entrada`, pero nunca llega a ejecutarse porque nunca se encuentra el
   registro correcto.

Adicionalmente, `esta_en_horario_comida` y el comando `detectar_incidencias` asumen
implícitamente que todo ocurre dentro del mismo día calendario.

## Decisión de diseño

Se representa el turno nocturno como **un solo registro de asistencia por turno**, con
`fecha` = el día en que inició el turno (igual que hoy). La entrada y la salida del
mismo turno viven en el mismo renglón de `RegistroAsistencia`, sin importar que la
salida ocurra después de medianoche.

Para saber cuándo un horario debe interpretarse como "cruza medianoche" se usa una
**bandera explícita** en el modelo, en vez de inferirlo implícitamente de las horas.
Esto evita que un error de captura (invertir accidentalmente hora de entrada/salida en
un turno diurno normal) se interprete silenciosamente como turno nocturno.

Alcance: **`TipoHorario` / `AsignacionHorario`** únicamente (confirmado como el modelo
que usa el hotel). El modelo semanal `Horario` no se modifica en este cambio.

## 1. Modelo de datos — `TipoHorario`

Nuevo campo:

```python
cruza_medianoche = models.BooleanField(
    default=False,
    verbose_name='Cruza medianoche',
    help_text='Activar si la salida ocurre al día siguiente (ej. turno 21:00 - 7:00)'
)
```

`clean()` se actualiza:

- Si `cruza_medianoche=False` y `hora_salida <= hora_entrada` → `ValidationError`
  (comportamiento actual, sigue protegiendo contra typos en turnos diurnos).
- Si `cruza_medianoche=True` y `hora_salida > hora_entrada` → `ValidationError`
  ("si el turno no cruza medianoche, desmarca la casilla").

`TipoHorarioSerializer` (horarios/serializers.py) agrega el campo `cruza_medianoche` a
`fields` y replica la misma validación cruzada en un método `validate()`, para que la
API de administración se comporte igual que el admin de Django (que llama
`full_clean()` a través del `ModelForm`).

`AsignacionHorario` no cambia de forma — sigue apuntando a un `TipoHorario`, que ahora
puede tener `cruza_medianoche=True`.

Migración: un solo campo booleano con `default=False`, sin impacto en datos existentes.

## 2. Resolución del "registro activo" (registros/models.py, registros/views.py)

Se agrega una función/helper `obtener_registro_activo(empleado, ahora_mexico)` que
sustituye el `get_or_create(fecha=hoy)` directo en los 4 endpoints de marcado y en
`verificar_rostro`:

1. Busca el registro de **hoy** (`fecha=hoy`). Si existe, es el candidato normal (igual
   que el comportamiento actual).
2. Si el registro de hoy no existe o no tiene `hora_entrada` todavía, busca el registro
   de **ayer** (`fecha=hoy - 1 día`) para el mismo empleado. Si ese registro tiene
   `hora_entrada`, no tiene `hora_salida`, y el horario vigente para esa fecha
   (`obtener_horario_del_dia(empleado, ayer)`) tiene `cruza_medianoche=True` → ese es el
   registro activo (turno nocturno en curso).
3. Si ninguna de las anteriores aplica → se crea el registro de hoy (comportamiento
   actual, sin cambios).

Reglas de negocio en `_marcar_asistencia`:

- **`entrada`**: si el helper resuelve al registro de **ayer** (turno nocturno todavía
  abierto), se rechaza con un mensaje explícito ("Tienes un turno nocturno sin cerrar
  del {fecha}, marca tu salida primero") en vez de proceder. Esto evita crear un tercer
  registro huérfano y obliga a cerrar el turno pendiente antes de abrir uno nuevo.
- **`salida` / `salida_comida` / `entrada_comida`**: operan sobre el registro activo
  resuelto por el helper (hoy o ayer), en vez de siempre crear uno nuevo con
  `fecha=hoy`.

`verificar_rostro` y `RegistroAsistencia.obtener_botones_disponibles` usan el mismo
helper, para que el kiosko muestre el botón correcto ("Salida") en vez de "Entrada"
cuando el empleado llega en la madrugada a cerrar su turno.

`calcular_horas_trabajadas` no requiere cambios: ya suma un día cuando
`hora_salida < hora_entrada`; el fix está en que ahora sí recibe el registro correcto
para ejecutarse.

## 3. Comida cruzando medianoche

`esta_en_horario_comida(hora_actual)` (en `TipoHorario` y `Horario`) hoy asume
`hora_inicio_comida <= hora_actual <= hora_fin_comida`, lo cual falla si la comida
también cruza medianoche (ej. 01:00–01:30am). Se ajusta a:

```python
def esta_en_horario_comida(self, hora_actual):
    if not self.tiene_comida or not self.hora_inicio_comida or not self.hora_fin_comida:
        return False
    if self.hora_inicio_comida <= self.hora_fin_comida:
        return self.hora_inicio_comida <= hora_actual <= self.hora_fin_comida
    # La comida cruza medianoche
    return hora_actual >= self.hora_inicio_comida or hora_actual <= self.hora_fin_comida
```

Este ajuste es independiente de `cruza_medianoche` del turno completo — es sólo una
comparación de rango horario que puede envolver medianoche por sí sola.

## 4. Incidencias (`detectar_incidencias`, `calcular_incidencias`)

El comando `detectar_incidencias` revisa "el día anterior" y marca `incidencia =
'sin_salida'` a cualquier registro con `hora_entrada` pero sin `hora_salida`. Para un
turno nocturno esto genera **falsos positivos**: si el comando corre de madrugada, la
salida real del turno todavía no ha ocurrido.

Ajuste: antes de marcar `sin_salida`, si el horario asociado al registro (vía
`obtener_horario_del_dia`) tiene `cruza_medianoche=True`, sólo se marca la incidencia si
ya transcurrió el tiempo suficiente desde la hora de salida esperada:

```
ahora_mexico >= datetime.combine(fecha_registro + 1 día, hora_salida_esperada) + tolerancia
```

Si el turno nocturno todavía está "a tiempo" de cerrar, se omite el registro en esa
corrida (se revisa en la siguiente ejecución del comando, o al día siguiente).

## 5. Fuera de alcance

- **Dashboard/reportes** (`checador/views.py`, ej. `registros_hoy` contado por
  `fecha=hoy`): un empleado nocturno que entró ayer y sigue trabajando después de
  medianoche no aparecerá en el conteo de "hoy" hasta que se cree su propio registro
  del día siguiente. Es un cambio de reportes, no de captura de asistencia — queda
  anotado como mejora futura, no se toca en este cambio.
- **Modelo `Horario` (semanal) y sus serializers**: el hotel usa
  `TipoHorario`/`AsignacionHorario`, así que `Horario` no se modifica. Si en el futuro
  se necesitan turnos nocturnos ahí también, aplica la misma receta (campo
  `cruza_medianoche`, misma validación cruzada).

## 6. Plan de pruebas

- `TipoHorario`: crear turno nocturno válido (`cruza_medianoche=True`,
  `hora_entrada=21:00`, `hora_salida=07:00`) se guarda sin error, vía modelo y vía
  `TipoHorarioSerializer`.
- `TipoHorario`: crear turno con `cruza_medianoche=True` pero `hora_salida > hora_entrada`
  falla con `ValidationError`.
- `TipoHorario`: crear turno con `cruza_medianoche=False` y `hora_salida <= hora_entrada`
  sigue fallando (regresión del comportamiento actual).
- Flujo completo: `marcar_entrada` a las 21:00 (fecha=D) + `marcar_salida` a las 07:00
  del día D+1 → un solo `RegistroAsistencia` con `fecha=D`, `hora_entrada=21:00`,
  `hora_salida=07:00`, y `horas_trabajadas` calculado correctamente (10h).
- `marcar_entrada` al día D+1 mientras el turno nocturno de D sigue sin `hora_salida` →
  rechazado con el mensaje de turno pendiente, no crea un tercer registro.
- `obtener_botones_disponibles` para un empleado con turno nocturno abierto de ayer
  devuelve `['salida']` (o `['salida_comida', 'salida']` si aplica comida), no
  `['entrada']`.
- `esta_en_horario_comida` con comida que cruza medianoche (ej. 01:00–01:30) devuelve
  `True` para horas dentro del rango envolvente y `False` fuera de él.
- `detectar_incidencias` ejecutado de madrugada sobre un turno nocturno en curso NO
  marca `sin_salida`; ejecutado después de la hora de salida esperada + tolerancia SÍ la
  marca si sigue sin `hora_salida`.
