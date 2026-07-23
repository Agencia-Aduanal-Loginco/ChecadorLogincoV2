# Diseño: Botones dinámicos en el flujo de checado (`/checador/`)

## Contexto

El sistema tiene dos páginas de reconocimiento facial para marcar asistencia:

- `/facial/` (`templates/facial_recognition.html`): página simple y desactualizada, solo con botones fijos de "Entrada" y "Salida", sin soporte de comida ni de estado. Queda fuera de alcance de este diseño.
- `/checador/` (`templates/facial_recognition_comida.html`): página completa con flujo de dos pasos (verificar rostro → mostrar acciones disponibles). Es la página objetivo de este diseño.

El backend ya calcula correctamente qué acciones corresponden al estado del día del empleado:

- `RegistroAsistencia.obtener_botones_disponibles()` (`registros/models.py`) devuelve la lista de botones válidos según los campos `hora_entrada`, `hora_salida_comida`, `hora_entrada_comida`, `hora_salida`, y — cuando el horario del empleado incluye comida — si la hora actual está dentro de la ventana de comida (`esta_en_horario_comida`).
- El endpoint `verificar_rostro` (`registros/views.py`) expone esa lista como `botones_disponibles` en la respuesta JSON, junto con `registro` (horas ya marcadas) y `mensaje_estado`.
- Los endpoints `marcar_entrada`, `marcar_salida_comida`, `marcar_entrada_comida`, `marcar_salida` ya validan en el servidor que la transición sea válida (p. ej. rechazan una segunda entrada), así que la UI es una capa de prevención de errores, no la única barrera.

El problema actual es puramente de presentación: `facial_recognition_comida.html` recibe `botones_disponibles` pero solo lo usa para habilitar/deshabilitar los 4 botones (`disabled` + opacidad reducida). Los 4 botones están siempre presentes en pantalla, lo que puede confundir al empleado sobre qué acción le corresponde.

## Objetivo

Que en `/checador/` solo estén presentes (visibles) los botones de acción que aplican al estado actual del registro del día, ocultando por completo el resto, conforme a este flujo:

1. Sin registros hoy → solo **Entrada**.
2. Con Entrada, fuera de la ventana de comida (o sin horario de comida configurado) → solo **Salida**.
3. Con Entrada, dentro de la ventana de comida → **Salir a Comer** y **Salida**.
4. Con Salida a comer registrada → solo **Regresar de Comer**.
5. Con Regreso de comer registrado → solo **Salida**.
6. Con Salida final registrada → ningún botón de acción; se muestra el mensaje de día completo.

Esta lógica de transición de estados ya está implementada en el backend (`obtener_botones_disponibles`) y no cambia. El alcance de este diseño es exclusivamente de frontend.

## Alcance

**Archivo modificado:** `templates/facial_recognition_comida.html` (JavaScript embebido, función `actualizarBotones` y el bloque de "día completo").

**Sin cambios en:**
- `registros/models.py` (`obtener_botones_disponibles`, `calcular_incidencias`)
- `registros/views.py` (`verificar_rostro`, `_marcar_asistencia`, `_generar_mensaje_estado`)
- `templates/facial_recognition.html` (página `/facial/`, fuera de alcance)
- Timeline visual, paso 1 (verificación de rostro), endpoints de marcado

## Diseño detallado

### 1. Ocultar en vez de deshabilitar

`actualizarBotones(disponibles)` se modifica para que, además de fijar `disabled`, oculte (`classList.add('hidden')`) los botones cuyo tipo no esté en el arreglo `disponibles`, y los muestre (`classList.remove('hidden')`) cuando sí lo esté:

```js
function actualizarBotones(disponibles) {
    const mapaBotones = {
        'entrada': btnEntrada,
        'salida_comida': btnSalidaComida,
        'entrada_comida': btnEntradaComida,
        'salida': btnSalida
    };

    Object.entries(mapaBotones).forEach(([tipo, btn]) => {
        const activo = disponibles.includes(tipo);
        btn.classList.toggle('hidden', !activo);
        btn.disabled = !activo;
        btn.classList.remove('ring-4', 'ring-offset-2', 'ring-green-300', 'ring-orange-300', 'ring-blue-300', 'ring-red-300');
        if (activo) {
            btn.classList.add('ring-4', 'ring-offset-2');
            const ringPorTipo = {
                entrada: 'ring-green-300',
                salida_comida: 'ring-orange-300',
                entrada_comida: 'ring-blue-300',
                salida: 'ring-red-300'
            };
            btn.classList.add(ringPorTipo[tipo]);
        }
    });

    document.getElementById('accionesContainer').classList.toggle('hidden', disponibles.length === 0);
    document.getElementById('diaCompletoMsg').classList.toggle('hidden', disponibles.length > 0);
}
```

Se conserva `disabled = true` en los botones ocultos como salvaguarda adicional (en caso de que queden en el DOM por algún estado transitorio), aunque la ocultación (`hidden`) es la barrera principal contra el error de usuario.

### 2. Contenedores nuevos: acciones vs. día completo

El bloque actual de "Botones de Acción" se envuelve en un contenedor `id="accionesContainer"`. El mensaje verde de día completo (que hoy vive dentro de `actualizarBotones` como HTML inyectado en `mensajeEstado`) se separa a un bloque propio `id="diaCompletoMsg"` (oculto por defecto), colocado junto a `accionesContainer`, para no pisar el `mensajeEstado` normal (que sigue mostrando el resumen de horas: "Entrada: 08:00 | Salida a comer: ... - Día completo").

Cuando `disponibles.length === 0`:
- `accionesContainer` se oculta (los 4 botones desaparecen).
- `diaCompletoMsg` se muestra con el texto "Todos los registros del día están completos".
- El botón "Verificar Otro Empleado" permanece visible siempre (no está dentro de `accionesContainer`), para permitir escanear al siguiente empleado.

### 3. Aplicación en ambos flujos de actualización

`actualizarBotones` ya se invoca desde los dos puntos donde se recibe `botones_disponibles` del backend:
- `mostrarEmpleado(data)` — tras la verificación inicial (paso 1 → paso 2).
- `verificarRostroSilencioso()` — tras marcar una acción, para refrescar el estado sin recargar la página.

No se requiere ningún punto de integración adicional.

## Casos borde (ya cubiertos por el backend, sin cambios)

- **Empleado sin horario de comida asignado:** `obtener_botones_disponibles` nunca incluye `salida_comida`/`entrada_comida`; con este diseño esos botones simplemente nunca se muestran para ese empleado.
- **Fuera de la ventana de comida:** solo se muestra `salida`, tal como ya decide el backend.
- **Reintento tras error del servidor** (p. ej. si `marcar_asistencia` rechaza la transición): el código ya restaura `actualizarBotones(botonesDisponibles)` con el último estado conocido en el `catch`/rama de error, así que el comportamiento de ocultar/mostrar se mantiene consistente.

## Fuera de alcance

- Unificar o retirar `/facial/`.
- Cambios al paso 1 (verificación de rostro) o al timeline visual.
- Cambios a la lógica de negocio del backend (ventana de comida, validaciones de transición).
