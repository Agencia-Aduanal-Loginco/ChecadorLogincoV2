# Migración de Cron a Django APScheduler

Este documento describe la migración del sistema de reportes automatizados desde cron a Django APScheduler.

## ¿Por qué cambiar?

### Ventajas de Django APScheduler sobre Cron

1. **Integración con Django**: Los jobs tienen acceso completo al ORM y configuración de Django
2. **Gestión desde Admin**: Se pueden ver jobs y ejecuciones desde el panel de administración
3. **Logging integrado**: Todas las ejecuciones se registran en la base de datos automáticamente
4. **Portabilidad**: Funciona en cualquier SO sin configurar cron (útil para Windows, Docker, etc.)
5. **No requiere configuración del servidor**: Todo está dentro de Django
6. **Mejor manejo de errores**: Captura excepciones y las registra automáticamente
7. **Testing más fácil**: Los jobs se pueden probar directamente en desarrollo

## Cambios realizados

### 1. Nueva dependencia
- **Agregado**: `django-apscheduler==0.6.2` a `requirements.txt`

### 2. Configuración de Django
- **Agregado**: `django_apscheduler` a `INSTALLED_APPS` en `settings.py`

### 3. Nuevo módulo: `reportes/scheduler.py`
Contiene toda la lógica del scheduler:
- `enviar_reporte_diario()`: Job para envío diario (Lun-Sab 11:50am)
- `enviar_reporte_semanal()`: Job para envío semanal (Viernes 11:50am)
- `enviar_reporte_quincenal()`: Job para envío quincenal (Días 14 y 29, 11:50am)
- `delete_old_job_executions()`: Limpieza de logs antiguos (Diario 00:00am)
- `start_scheduler()`: Inicializa el scheduler con todos los jobs

### 4. Inicialización automática
- **Modificado**: `reportes/apps.py` para iniciar el scheduler al arrancar Django
- Se ejecuta automáticamente con `runserver` o `gunicorn`
- No se ejecuta durante migraciones o comandos de shell

### 5. Nuevo comando de gestión
- **Creado**: `python manage.py scheduler` con tres subcomandos:
  - `status`: Ver estado de jobs programados
  - `start`: Iniciar scheduler manualmente
  - `list`: Listar últimas ejecuciones

### 6. Archivo obsoleto
- **Deprecado**: `crontab.txt` (mantener como referencia, pero ya no usar)

## Instalación

### Paso 1: Instalar dependencias

```bash
source .venvChecadorLoginco/bin/activate
pip install -r requirements.txt
```

### Paso 2: Ejecutar migraciones

Django APScheduler necesita crear sus tablas en la base de datos:

```bash
python manage.py migrate
```

Esto creará las siguientes tablas:
- `django_apscheduler_djangojob`: Almacena los jobs programados
- `django_apscheduler_djangojobexecution`: Almacena el historial de ejecuciones

### Paso 3: Desactivar cron (si estaba activo)

```bash
# Ver crontabs actuales
crontab -l

# Remover crontabs del proyecto (si existen)
crontab -r  # O editar manualmente con: crontab -e
```

### Paso 4: Iniciar el servidor

El scheduler se inicia automáticamente al arrancar Django:

```bash
python manage.py runserver
```

Verás en los logs:
```
Job programado: Reporte diario (Lun-Sab 11:50am)
Job programado: Reporte semanal (Viernes 11:50am)
Job programado: Reporte quincenal (Dias 14 y 29, 11:50am)
Job programado: Limpieza de ejecuciones antiguas (Diario 00:00am)
Scheduler iniciado exitosamente
```

## Uso

### Ver estado de jobs

```bash
python manage.py scheduler status
```

Salida de ejemplo:
```
Jobs programados: 4

Job: Envio de reporte diario
  ID: reporte_diario
  Siguiente ejecucion: 2026-01-31 11:50:00
  Ultima ejecucion: 2026-01-30 11:50:12
  Estado: Success

Job: Envio de reporte semanal
  ID: reporte_semanal
  Siguiente ejecucion: 2026-01-31 11:50:00
  ...
```

### Listar últimas ejecuciones

```bash
# Últimas 10 ejecuciones (default)
python manage.py scheduler list

# Últimas 20 ejecuciones
python manage.py scheduler list --limit 20
```

### Iniciar scheduler manualmente

```bash
python manage.py scheduler start
```

### Envío manual de reportes

El comando `enviar_reporte` sigue funcionando igual:

```bash
# Envío manual diario
python manage.py enviar_reporte diario

# Envío manual semanal
python manage.py enviar_reporte semanal

# Envío a email de prueba
python manage.py enviar_reporte diario --email test@example.com
```

### Ver historial en el Admin

1. Acceder al panel de administración: http://localhost:8000/admin
2. Navegar a:
   - **Django Apscheduler → Django jobs**: Ver jobs programados
   - **Django Apscheduler → Django job executions**: Ver historial de ejecuciones

## Horarios configurados

Los horarios son idénticos a los configurados en cron:

| Tipo | Frecuencia | Hora | Días |
|------|-----------|------|------|
| Diario | Lunes a Sábado | 11:50am | - |
| Semanal | Viernes | 11:50am | - |
| Quincenal | Días 14 y 29 | 11:50am | De cada mes |
| Limpieza | Diario | 00:00am | Todos los días |

Para cambiar horarios, edita `reportes/scheduler.py` y modifica los `CronTrigger`.

## Producción con Gunicorn

El scheduler se inicia automáticamente con Gunicorn:

```bash
gunicorn checador.wsgi:application
```

**IMPORTANTE**: Gunicorn debe ejecutarse con un solo worker si usas el scheduler:

```bash
# Correcto para scheduler
gunicorn checador.wsgi:application --workers 1

# Si necesitas múltiples workers, ejecuta el scheduler por separado:
gunicorn checador.wsgi:application --workers 4 &
python manage.py scheduler start
```

## Logging

Los logs del scheduler se escriben en:
- **Console**: Durante desarrollo con `runserver`
- **LogReporte model**: Cada envío de reporte se registra en la base de datos
- **DjangoJobExecution**: Cada ejecución de job (éxito o error) se registra automáticamente

## Troubleshooting

### El scheduler no inicia

**Problema**: No ves los mensajes "Job programado..." al iniciar Django

**Solución**:
1. Verifica que `django_apscheduler` esté en `INSTALLED_APPS`
2. Ejecuta `python manage.py migrate`
3. Revisa logs para errores de importación

### Jobs no se ejecutan a la hora programada

**Problema**: Llega la hora pero el job no se ejecuta

**Solución**:
1. Verifica que el servidor esté corriendo: `python manage.py scheduler status`
2. Revisa la zona horaria en `settings.py`: `TIME_ZONE = 'America/Mexico_City'`
3. Verifica que no hayas cerrado el servidor Django

### Múltiples instancias del scheduler

**Problema**: Reportes se envían duplicados

**Solución**:
- Django APScheduler previene esto con `max_instances=1`
- Si usas múltiples workers en producción, ejecuta el scheduler en un proceso separado

### Ver logs de ejecución

```bash
# Ver últimas 20 ejecuciones
python manage.py scheduler list --limit 20

# Ver en el admin
# Ir a: Django Apscheduler → Django job executions
```

## Ventajas adicionales

### 1. Testing en desarrollo
Puedes probar los jobs inmediatamente sin esperar al horario:

```python
# En Django shell
from reportes.scheduler import enviar_reporte_diario
enviar_reporte_diario()
```

### 2. Monitoreo visual
El admin de Django muestra:
- Próxima ejecución de cada job
- Historial completo de ejecuciones
- Errores con stack traces completos
- Duración de cada ejecución

### 3. Configuración dinámica
Puedes modificar horarios sin editar crontab:
```python
# Cambiar horario en reportes/scheduler.py
CronTrigger(day_of_week="mon-sat", hour=12, minute=0)  # Cambiar a 12:00pm
# Reiniciar servidor
```

## Comparación: Antes vs Después

### Antes (Cron)
```bash
# En crontab.txt
50 11 * * 1-6 cd $PROYECTO && $PYTHON $MANAGE enviar_reporte diario >> $LOG 2>&1
50 11 * * 5 cd $PROYECTO && $PYTHON $MANAGE enviar_reporte semanal >> $LOG 2>&1
50 11 14,29 * * cd $PROYECTO && $PYTHON $MANAGE enviar_reporte quincenal >> $LOG 2>&1

# Instalar:
crontab /ruta/al/proyecto/crontab.txt

# Ver logs:
cat logs/cron.log
```

### Después (Django APScheduler)
```bash
# Instalar:
pip install -r requirements.txt
python manage.py migrate

# Iniciar (automático):
python manage.py runserver

# Ver estado:
python manage.py scheduler status

# Ver logs:
python manage.py scheduler list
```

## Referencias

- [Django APScheduler Documentation](https://github.com/jcass77/django-apscheduler)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- Código fuente: `reportes/scheduler.py`
- Management command: `reportes/management/commands/scheduler.py`
