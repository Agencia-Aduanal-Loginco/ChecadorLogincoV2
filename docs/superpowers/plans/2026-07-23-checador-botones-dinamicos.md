# Botones Dinámicos en Checador - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** En `/checador/`, mostrar únicamente los botones de acción (Entrada / Salir a Comer / Regresar de Comer / Salida) que aplican al estado actual del registro del día del empleado, ocultando por completo (no solo deshabilitando) los demás.

**Architecture:** Cambio exclusivamente de frontend sobre `templates/facial_recognition_comida.html`. El backend (`RegistroAsistencia.obtener_botones_disponibles()` en `registros/models.py` y el endpoint `verificar_rostro` en `registros/views.py`) ya calcula correctamente la lista `botones_disponibles`; solo se reescribe la función JS `actualizarBotones()` para ocultar (`classList.add('hidden')`) los botones no incluidos en esa lista, y se separa el estado "día completo" en su propio bloque visual en vez de sobreescribir el mensaje de estado.

**Tech Stack:** Django 6.0 (server-rendered template), JavaScript vanilla embebido (sin framework ni bundler), Tailwind (CDN) para clases de utilidad incluida `hidden`.

## Global Constraints

- Solo se modifica `templates/facial_recognition_comida.html`. No tocar `templates/facial_recognition.html` (`/facial/`), `registros/models.py`, ni `registros/views.py`.
- El cálculo de qué botones corresponden (incluida la ventana de comida `esta_en_horario_comida`) permanece sin cambios en el backend.
- El proyecto no tiene framework de pruebas de JavaScript (no hay `package.json`). La verificación de comportamiento JS se hace en navegador real, no con un test runner nuevo.
- Ejecutar pruebas Django con: `source .venvChecadorLoginco/bin/activate && python manage.py test registros`.
- Levantar el servidor de desarrollo con: `source .venvChecadorLoginco/bin/activate && python manage.py runserver`.

---

### Task 1: Ocultar botones no aplicables y separar el mensaje de "día completo"

**Files:**
- Modify: `templates/facial_recognition_comida.html:229-256` (bloque "Botones de Acción" + botón "Verificar Otro Empleado")
- Modify: `templates/facial_recognition_comida.html:502-543` (función `actualizarBotones`)
- Test: `registros/tests.py`

**Interfaces:**
- Consumes: la respuesta JSON de `/api/registros/verificar_rostro/` ya expone `data.botones_disponibles` (array de strings entre `'entrada'`, `'salida_comida'`, `'entrada_comida'`, `'salida'`) — sin cambios, ya existente en `registros/views.py:145`.
- Produces: elementos del DOM con `id="accionesContainer"` (envuelve los 4 botones) e `id="diaCompletoMsg"` (mensaje mostrado cuando `botones_disponibles` es `[]`), consumidos por la función `actualizarBotones(disponibles)`.

- [ ] **Step 1: Escribir las pruebas que fallan**

Reemplaza el contenido de `registros/tests.py`:

```python
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
```

- [ ] **Step 2: Ejecutar las pruebas y confirmar que fallan**

Run: `source .venvChecadorLoginco/bin/activate && python manage.py test registros -v 2`
Expected: `FAIL` en las tres pruebas nuevas — `accionesContainer` y `diaCompletoMsg` no existen aún en el template, y `actualizarBotones` todavía usa la lógica antigua de solo `disabled`.

- [ ] **Step 3: Reescribir el bloque de botones de acción en el template**

En `templates/facial_recognition_comida.html`, sustituye el bloque completo desde el comentario `<!-- Botones de Acción -->` hasta el cierre del `<button id="btnVerificarNuevo">` (líneas 229-256 en la versión actual) por:

```html
                        <!-- Botones de Acción -->
                        <div id="accionesContainer" class="space-y-3">
                            <button id="btnEntrada" class="btn-action w-full bg-green-600 hover:bg-green-700 text-white px-6 py-4 rounded-xl font-bold text-lg transition transform hover:scale-105 shadow-lg disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none" disabled title="No disponible en este momento">
                                <i class="fas fa-door-open mr-2"></i>
                                Marcar Entrada
                            </button>

                            <button id="btnSalidaComida" class="btn-action w-full bg-orange-600 hover:bg-orange-700 text-white px-6 py-4 rounded-xl font-bold text-lg transition transform hover:scale-105 shadow-lg disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none" disabled title="No disponible en este momento">
                                <i class="fas fa-utensils mr-2"></i>
                                Salir a Comer
                            </button>

                            <button id="btnEntradaComida" class="btn-action w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-4 rounded-xl font-bold text-lg transition transform hover:scale-105 shadow-lg disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none" disabled title="No disponible en este momento">
                                <i class="fas fa-arrow-rotate-left mr-2"></i>
                                Regresar de Comer
                            </button>

                            <button id="btnSalida" class="btn-action w-full bg-red-600 hover:bg-red-700 text-white px-6 py-4 rounded-xl font-bold text-lg transition transform hover:scale-105 shadow-lg disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none" disabled title="No disponible en este momento">
                                <i class="fas fa-home mr-2"></i>
                                Marcar Salida Final
                            </button>
                        </div>

                        <!-- Mensaje de día completo (se muestra cuando no hay botones disponibles) -->
                        <div id="diaCompletoMsg" class="hidden bg-green-50 border-l-4 border-green-500 p-4 rounded">
                            <p class="text-sm text-green-700 font-semibold">
                                <i class="fas fa-check-circle mr-2"></i>
                                Todos los registros del día están completos
                            </p>
                        </div>

                        <!-- Botón para verificar de nuevo -->
                        <button id="btnVerificarNuevo" class="w-full bg-gray-600 hover:bg-gray-700 text-white px-4 py-3 rounded-lg font-semibold transition">
                            <i class="fas fa-redo mr-2"></i>
                            Verificar Otro Empleado
                        </button>
```

- [ ] **Step 4: Reescribir `actualizarBotones()`**

En el mismo archivo, sustituye la función `actualizarBotones` completa (líneas 502-543 en la versión actual, desde `// Actualizar estado de botones` hasta su cierre `}`) por:

```javascript
        // Actualizar estado de botones: muestra únicamente los aplicables
        function actualizarBotones(disponibles) {
            const mapaBotones = {
                'entrada': btnEntrada,
                'salida_comida': btnSalidaComida,
                'entrada_comida': btnEntradaComida,
                'salida': btnSalida
            };
            const ringPorTipo = {
                'entrada': 'ring-green-300',
                'salida_comida': 'ring-orange-300',
                'entrada_comida': 'ring-blue-300',
                'salida': 'ring-red-300'
            };

            Object.entries(mapaBotones).forEach(([tipo, btn]) => {
                const activo = disponibles.includes(tipo);
                btn.classList.toggle('hidden', !activo);
                btn.disabled = !activo;
                btn.classList.remove('ring-4', 'ring-offset-2', 'ring-green-300', 'ring-orange-300', 'ring-blue-300', 'ring-red-300');
                if (activo) {
                    btn.classList.add('ring-4', 'ring-offset-2', ringPorTipo[tipo]);
                }
            });

            document.getElementById('accionesContainer').classList.toggle('hidden', disponibles.length === 0);
            document.getElementById('diaCompletoMsg').classList.toggle('hidden', disponibles.length > 0);
        }
```

Nota: esta versión ya **no** sobreescribe `mensajeEstado` cuando `disponibles` está vacío — ese texto (`"Entrada: 08:00 | ... - Dia completo"`) lo sigue controlando `mostrarEmpleado()`/`verificarRostroSilencioso()` vía `data.mensaje_estado`, que ya lo maneja `_generar_mensaje_estado()` en el backend sin cambios.

- [ ] **Step 5: Ejecutar las pruebas y confirmar que pasan**

Run: `source .venvChecadorLoginco/bin/activate && python manage.py test registros -v 2`
Expected: `OK` — las tres pruebas de `FacialRecognitionComidaTemplateTests` pasan.

- [ ] **Step 6: Commit**

```bash
git add templates/facial_recognition_comida.html registros/tests.py
git commit -m "$(cat <<'EOF'
Ocultar botones no aplicables en el flujo de checador

Solo se muestran los botones de accion que corresponden al estado
actual del registro del dia (entrada, salida a comer, entrada de
comer, salida), en vez de mostrarlos siempre deshabilitados. Cuando
el dia esta completo se oculta el bloque de botones y se muestra un
mensaje dedicado.
EOF
)"
```

---

### Task 2: Verificación en navegador de los 6 estados del flujo

**Files:**
- Ninguno modificado — tarea de verificación manual/browser sobre el resultado de Task 1.

**Interfaces:**
- Consumes: `actualizarBotones(disponibles)` y los elementos `#accionesContainer`, `#diaCompletoMsg`, `#btnEntrada`, `#btnSalidaComida`, `#btnEntradaComida`, `#btnSalida` producidos en Task 1.
- Produces: confirmación de que el comportamiento visual coincide con el diseño antes de dar la tarea por completa (requisito del proyecto para cambios de UI).

Esta verificación evita depender de una cámara real o de un empleado con rostro registrado: se invoca `actualizarBotones()` directamente desde la consola del navegador con arreglos sintéticos que representan cada uno de los 6 estados descritos en el spec, y se lee el estado resultante del DOM.

- [ ] **Step 1: Levantar el servidor de desarrollo**

Run: `source .venvChecadorLoginco/bin/activate && python manage.py runserver`
Expected: servidor escuchando en `http://127.0.0.1:8000/`.

- [ ] **Step 2: Abrir `/checador/` en el navegador y forzar el paso 2**

Navegar a `http://127.0.0.1:8000/checador/`. Luego, en la consola del navegador (DevTools) o vía la herramienta de automatización de Chrome, ejecutar:

```javascript
document.getElementById('paso1').classList.add('hidden');
document.getElementById('paso2').classList.remove('hidden');
```

Expected: el panel de "Paso 2: Panel de Empleado" se hace visible (aunque sin datos de empleado, ya que no se llamó a `mostrarEmpleado`).

- [ ] **Step 3: Verificar cada uno de los 5 arreglos distintos de `botones_disponibles`**

Para cada arreglo de la tabla, ejecutar en consola `actualizarBotones(<arreglo>)` y luego leer el estado con:

```javascript
JSON.stringify({
  entrada: !btnEntrada.classList.contains('hidden'),
  salida_comida: !btnSalidaComida.classList.contains('hidden'),
  entrada_comida: !btnEntradaComida.classList.contains('hidden'),
  salida: !btnSalida.classList.contains('hidden'),
  accionesContainer: !document.getElementById('accionesContainer').classList.contains('hidden'),
  diaCompletoMsg: !document.getElementById('diaCompletoMsg').classList.contains('hidden')
})
```

| Estado del spec | `actualizarBotones([...])` | Resultado esperado (`true` = visible) |
|---|---|---|
| 1. Sin registros hoy | `['entrada']` | `{"entrada":true,"salida_comida":false,"entrada_comida":false,"salida":false,"accionesContainer":true,"diaCompletoMsg":false}` |
| 2. Entrada, fuera de ventana de comida | `['salida']` | `{"entrada":false,"salida_comida":false,"entrada_comida":false,"salida":true,"accionesContainer":true,"diaCompletoMsg":false}` |
| 3. Entrada, dentro de ventana de comida | `['salida_comida','salida']` | `{"entrada":false,"salida_comida":true,"entrada_comida":false,"salida":true,"accionesContainer":true,"diaCompletoMsg":false}` |
| 4. Con salida a comer registrada | `['entrada_comida']` | `{"entrada":false,"salida_comida":false,"entrada_comida":true,"salida":false,"accionesContainer":true,"diaCompletoMsg":false}` |
| 5. Con regreso de comer registrado | `['salida']` | (igual que estado 2) |
| 6. Día completo | `[]` | `{"entrada":false,"salida_comida":false,"entrada_comida":false,"salida":false,"accionesContainer":false,"diaCompletoMsg":true}` |

Expected: el JSON devuelto por cada llamada coincide exactamente con la columna "Resultado esperado" de su fila.

- [ ] **Step 4: Verificar que el botón "Verificar Otro Empleado" permanece visible en todos los casos**

En cualquiera de los estados anteriores, ejecutar:

```javascript
!document.getElementById('btnVerificarNuevo').classList.contains('hidden')
```

Expected: `true` en todos los casos (ese botón no forma parte de `accionesContainer` y nunca se oculta).

- [ ] **Step 5: Registrar el resultado**

Si algún estado de la tabla del Step 3 no coincide con el resultado esperado, es un defecto en la implementación de Task 1: volver a `actualizarBotones()` en `templates/facial_recognition_comida.html`, corregir la condición correspondiente, repetir Task 1 Step 5 (pruebas Django) y este Task 2 desde el Step 3, y hacer un commit adicional con la corrección antes de continuar. Si todos los estados coinciden, la tarea queda completa sin cambios adicionales (no requiere commit, Task 1 ya contiene el código verificado).
