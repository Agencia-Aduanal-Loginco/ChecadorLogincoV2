# Multi-empresa: agrupación de empleados y separación de reportes

**Fecha:** 2026-09-11
**Estado:** Aprobado para planeación

## Contexto

El sistema ChecadorLogincoV2 fue diseñado para una sola empresa (Loginco). Ahora se
usará también para otras empresas, compartiendo la misma instalación. Se necesita:

1. Representar el nombre de la empresa como entidad de datos.
2. Agrupar/filtrar empleados por empresa en la administración.
3. Separar los reportes automáticos de asistencia por empresa (un correo por
   empresa, con sus propios destinatarios y solo sus datos).

## Decisiones de alcance (confirmadas con el usuario)

- **Aislamiento:** solo agrupación/filtro. No hay control de acceso por empresa —
  cualquier usuario staff sigue viendo y administrando todas las empresas.
- **Asociación empleado↔empresa:** campo directo `empresa` (FK) en `Empleado`, no
  derivado del departamento.
- **Reportes separados:** solo los reportes de asistencia (`diario`, `semanal`,
  `quincenal`). Los reportes de `permisos`, `tickets_it` e `inventario` no se
  tocan.
- **Checador (reconocimiento facial):** se mantiene un único checador
  (`/facial/`) para todas las empresas. El reconocimiento facial sigue buscando
  entre todos los empleados sin importar empresa; la empresa es solo un atributo
  del empleado ya identificado.
- **Campos de `Empresa`:** solo lo básico — `nombre`, `codigo`, `activo`. Sin
  datos de contacto ni logo por ahora.
- **Empresa por defecto:** "Loginco", para no dejar huérfanos a los empleados
  existentes.

## Fuera de alcance (explícito)

- Control de acceso / permisos por empresa para usuarios staff.
- Vincular `Departamento` (app `organizacion`) a `Empresa`. Queda como
  limitación conocida: si dos empresas necesitan un departamento con el mismo
  `nombre`/`codigo`, hoy chocarían con el `unique=True` existente en
  `Departamento`. No se resuelve en este trabajo.
- Reportes de `permisos`, `tickets_it` e `inventario`.
- Branding (logo, colores) por empresa en los reportes.
- Restringir el auto-registro público (`/register/`). Ya era abierto (cualquier
  visitante podía crearse como empleado) antes de este trabajo; ahora esa
  misma persona también elige su empresa. Se decidió explícitamente (con el
  usuario) dejarlo así por ahora — es una limitación conocida, no un defecto.
- Checadores/URLs separados por empresa.

## Diseño

### 1. Modelo `Empresa` (app `organizacion`)

```python
class Empresa(models.Model):
    nombre = models.CharField(max_length=150, unique=True, verbose_name='Nombre')
    codigo = models.CharField(max_length=20, unique=True, verbose_name='Código')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
```

Se registra en `organizacion/admin.py` con `EmpresaAdmin` (list_display:
`codigo`, `nombre`, `activo`; search_fields: `codigo`, `nombre`).

### 2. `Empleado.empresa`

Nuevo campo en `empleados/models.py`:

```python
empresa = models.ForeignKey(
    'organizacion.Empresa',
    on_delete=models.PROTECT,
    related_name='empleados',
    verbose_name='Empresa',
)
```

`on_delete=PROTECT` evita borrar por accidente una empresa que todavía tiene
empleados.

**Migración de datos:** se crea (o se obtiene) la `Empresa` "Loginco"
(`codigo='LOGINCO'`) y se asignan todos los `Empleado` existentes a ella, antes
de volver el campo no-nullable (patrón: migración 1 agrega el campo con
`null=True`, migración 2 hace el data migration y asigna default, migración 3
altera el campo a `null=False`).

### 3. Administración de empleados

- `EmpleadoAdmin` (`empleados/admin.py`): agregar `empresa` a `list_display`,
  `list_filter`, `autocomplete_fields`, y al fieldset "Información del
  Empleado".
- Registro público (`checador/views.py::register_view` +
  `templates/auth/register.html`): agregar selector `<select name="empresa">`
  obligatorio, poblado desde `Empresa.objects.filter(activo=True)`. Se guarda
  al crear el `Empleado`.

### 4. Lista de empleados agrupada por empresa

`checador/views.py::empleados_lista_view` y
`templates/empleados/lista.html`:

- Nuevo query param `empresa` (mismo patrón que el filtro `departamento`
  existente), con un `<select>` poblado desde `Empresa.objects.filter(activo=True)`.
- Cuando **no** hay filtro de empresa aplicado, la vista agrupa los empleados
  por empresa (`empleados.order_by('empresa__nombre', 'codigo_empleado')`) y el
  template renderiza una fila de encabezado de sección por cada empresa (ej.
  "🏢 Loginco — 12 empleados") antes de sus filas.
- Cuando hay un filtro de empresa aplicado, se muestra la tabla plana normal
  (sin encabezados de sección, ya que todos son de la misma empresa).

### 5. Reportes de asistencia separados por empresa

**`reportes/models.py::ConfiguracionReporte`:**

- Nuevo campo `empresa = models.ForeignKey('organizacion.Empresa', null=True, blank=True, on_delete=models.CASCADE, related_name='configuraciones_reporte')`.
  Nulo para los tipos que no se separan (`permisos`, `tickets_it`,
  `inventario`); obligatorio (validado en `clean()`) para `diario`, `semanal`,
  `quincenal`.
- Se reemplaza `unique=True` en `tipo` por restricciones a nivel de modelo:
  ```python
  class Meta:
      constraints = [
          models.UniqueConstraint(
              fields=['tipo'], condition=models.Q(empresa__isnull=True),
              name='config_reporte_unico_sin_empresa'
          ),
          models.UniqueConstraint(
              fields=['tipo', 'empresa'], condition=models.Q(empresa__isnull=False),
              name='config_reporte_unico_por_empresa'
          ),
      ]
  ```
- Data migration: las configuraciones existentes de `diario`/`semanal`/
  `quincenal` se reasignan a la empresa "Loginco", conservando sus
  destinatarios (`DestinatarioReporte`) sin cambios.

**`reportes/models.py::LogReporte`:** nuevo campo `empresa` (FK nullable,
`on_delete=SET_NULL`) para auditar qué empresa recibió cada envío.

**`reportes/services/calculos.py::obtener_datos_reporte`:**

```python
def obtener_datos_reporte(fecha_inicio, fecha_fin, empresa=None):
    empleados = Empleado.objects.filter(activo=True, ...)
    if empresa is not None:
        empleados = empleados.filter(empresa=empresa)
    ...
    return {..., 'empresa': empresa, ...}
```

`registros` se filtra igual vía `empleado__empresa=empresa` cuando aplica.

**`reportes/services/generador_email.py::enviar_reporte`:** agrega parámetro
opcional `empresa=None`; cuando no hay `asunto_custom`, el asunto incluye el
nombre de la empresa: `f'Reporte {periodo} de {categoria} - {empresa.nombre} - {fecha_inicio} al {fecha_fin}'`.
Los templates de email (`reportes/templates/reportes/email/reporte_*.html`)
muestran el nombre de la empresa en el encabezado cuando `datos.empresa` está
presente.

**`reportes/scheduler.py`:** los tres jobs (`enviar_reporte_diario`,
`enviar_reporte_semanal`, `enviar_reporte_quincenal`) cambian de
`ConfiguracionReporte.objects.filter(tipo=X, activo=True).first()` a iterar
sobre `ConfiguracionReporte.objects.filter(tipo=X, activo=True)` (puede haber
varias, una por empresa), generando y enviando un reporte independiente por
cada configuración/empresa, y registrando un `LogReporte` por cada envío.

### 6. Facial recognition / checador

Sin cambios. El servicio (`registros/services/facial_recognition.py`) sigue
comparando contra los embeddings de todos los empleados activos, sin importar
empresa. Una vez identificado el empleado, su `empresa` ya queda disponible
como atributo para cualquier uso posterior (reportes, listados).

## Testing

- `organizacion`: test de creación de `Empresa`, `__str__`, unicidad de
  `codigo`/`nombre`.
- `empleados`: test de que `Empleado` requiere `empresa`; test de migración de
  datos (empleados existentes quedan asignados a "Loginco").
- `checador` (vistas): test de filtro por empresa en `empleados_lista_view`;
  test de agrupación (sin filtro, aparecen encabezados de sección por
  empresa).
- `reportes`: test de que `obtener_datos_reporte` filtra correctamente por
  empresa; test de la restricción `UniqueConstraint` condicional en
  `ConfiguracionReporte`; test de que el scheduler envía un correo por cada
  configuración activa (mockeando `enviar_reporte`).

## Migraciones (orden)

1. `organizacion`: crear modelo `Empresa`.
2. `empleados`: agregar `empresa` FK nullable a `Empleado`.
3. `empleados`: data migration — crear/obtener "Loginco", asignar a todos los
   empleados existentes.
4. `empleados`: alterar `empresa` a `null=False`.
5. `reportes`: agregar `empresa` FK nullable a `ConfiguracionReporte` y
   `LogReporte`; agregar los `UniqueConstraint` condicionales (reemplazando
   `unique=True` de `tipo`).
6. `reportes`: data migration — asignar "Loginco" a las configuraciones
   existentes de `diario`/`semanal`/`quincenal`.
