# Scheduler Automático de Reportes

Sistema de envío automático de reportes de asistencia usando **Django APScheduler**.

## 🚀 Inicio Rápido

### En Desarrollo

El scheduler se inicia automáticamente al ejecutar Django:

```bash
source .venvChecadorLoginco/bin/activate
python manage.py runserver
```

### En Producción

Con Gunicorn (single worker):

```bash
gunicorn checador.wsgi:application --workers 1
```

Con múltiples workers, ejecuta el scheduler por separado:

```bash
gunicorn checador.wsgi:application --workers 4 &
python manage.py scheduler start
```

## 📅 Horarios Configurados

| Tipo | Frecuencia | Hora |
|------|-----------|------|
| Diario | Lunes a Sábado | 11:50am |
| Semanal | Viernes | 11:50am |
| Quincenal | Días 14 y 29 | 11:50am |
| Limpieza | Todos los días | 00:00am |

## 🔧 Comandos Disponibles

### Ver estado de jobs programados

```bash
python manage.py scheduler status
```

Muestra:
- Jobs activos
- Próxima ejecución
- Última ejecución y estado

### Ver historial de ejecuciones

```bash
# Últimas 10 ejecuciones
python manage.py scheduler list

# Últimas 20 ejecuciones
python manage.py scheduler list --limit 20
```

### Iniciar scheduler manualmente

```bash
python manage.py scheduler start
```

### Enviar reporte manualmente (sin esperar horario)

```bash
# Enviar reporte del día
python manage.py enviar_reporte diario

# Enviar reporte semanal
python manage.py enviar_reporte semanal

# Enviar reporte quincenal
python manage.py enviar_reporte quincenal

# Enviar a email de prueba
python manage.py enviar_reporte diario --email test@example.com
```

## 📊 Monitoreo

### Desde la consola

```bash
# Ver estado
python manage.py scheduler status

# Ver últimas ejecuciones
python manage.py scheduler list --limit 20
```

### Desde el Admin de Django

1. Acceder a: `http://localhost:8000/admin`
2. Navegar a **Django Apscheduler**:
   - **Django jobs**: Ver jobs programados y próximas ejecuciones
   - **Django job executions**: Ver historial completo con errores

### Logs en la base de datos

Los reportes enviados se registran en:
- Modelo `LogReporte`: Ver en Admin → Reportes → Logs de Reportes
- Modelo `DjangoJobExecution`: Ver en Admin → Django Apscheduler

## ⚙️ Configuración

### Cambiar horarios

Editar `reportes/scheduler.py`, sección `start_scheduler()`:

```python
# Ejemplo: Cambiar reporte diario a 9:00am
scheduler.add_job(
    enviar_reporte_diario,
    trigger=CronTrigger(day_of_week="mon-sat", hour=9, minute=0),  # Cambiar aquí
    id="reporte_diario",
    max_instances=1,
    replace_existing=True,
    name="Envio de reporte diario"
)
```

Después reiniciar Django.

### Zona horaria

Configurada en `checador/settings.py`:

```python
TIME_ZONE = 'America/Mexico_City'
```

## 🐛 Troubleshooting

### Los jobs no aparecen

**Síntoma**: `python manage.py scheduler status` muestra "No hay jobs programados"

**Solución**:
```bash
# Iniciar scheduler manualmente
python manage.py scheduler start

# O iniciar el servidor
python manage.py runserver
```

### Jobs no se ejecutan

**Síntoma**: Llega la hora pero no se envía el reporte

**Solución**:
1. Verificar que Django está corriendo
2. Verificar zona horaria en `settings.py`
3. Revisar logs en admin: Django Apscheduler → Django job executions

### Error al enviar reportes

**Síntoma**: Job se ejecuta pero falla el envío

**Solución**:
1. Verificar configuración de SendGrid (`SENDGRID_API_KEY`)
2. Verificar destinatarios activos en Admin → Reportes → Configuración de Reportes
3. Ver error detallado en Admin → Reportes → Logs de Reportes
4. Ver stack trace completo en Admin → Django Apscheduler → Django job executions

### Reportes duplicados

**Síntoma**: Se envían múltiples reportes a la misma hora

**Solución**:
- Si usas Gunicorn con múltiples workers, ejecuta scheduler en proceso separado
- Verificar que `max_instances=1` en `reportes/scheduler.py`

## 📚 Documentación Completa

- **Guía de migración**: `SCHEDULER_MIGRATION.md`
- **Resumen de cambios**: `MIGRATION_SUMMARY.md`
- **Guía de desarrollo**: `WARP.md`

## 🔗 Referencias

- [Django APScheduler](https://github.com/jcass77/django-apscheduler)
- [APScheduler](https://apscheduler.readthedocs.io/)
- Código: `reportes/scheduler.py`
- Management command: `reportes/management/commands/scheduler.py`

## ✅ Ventajas sobre Cron

1. ✨ Todo dentro de Django - sin configuración del servidor
2. 🔍 Logs automáticos en base de datos
3. 👁️ Monitoreo visual desde admin de Django
4. 🌍 Funciona en cualquier SO (Windows, Linux, macOS, Docker)
5. 🧪 Fácil de probar en desarrollo
6. 🔧 Configuración en Python en lugar de sintaxis cron
7. 🔌 Integración completa con ORM y settings de Django

## 💡 Tips

### Probar jobs inmediatamente

En lugar de esperar al horario programado:

```bash
# Opción 1: Comando manual
python manage.py enviar_reporte diario

# Opción 2: Python shell
python manage.py shell
>>> from reportes.scheduler import enviar_reporte_diario
>>> enviar_reporte_diario()
```

### Ver próxima ejecución

```bash
python manage.py scheduler status | grep "Siguiente ejecucion"
```

### Limpiar jobs antiguos manualmente

```python
# En shell de Django
from django_apscheduler.models import DjangoJobExecution
from django.utils import timezone
from datetime import timedelta

# Eliminar ejecuciones mayores a 30 días
fecha_limite = timezone.now() - timedelta(days=30)
DjangoJobExecution.objects.filter(run_time__lt=fecha_limite).delete()
```

---

**Última actualización**: 2026-01-30  
**Versión**: 1.0  
**Requiere**: Django 6.0, django-apscheduler 0.6.2
