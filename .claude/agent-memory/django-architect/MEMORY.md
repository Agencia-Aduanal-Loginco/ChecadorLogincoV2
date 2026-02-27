# MEMORY.md - ChecadorLogincoV2 (Django Architect)

## Identidad del Proyecto
- Sistema de Control de Asistencias con reconocimiento facial para Loginco
- Django 6.0 + DRF + face_recognition/dlib/OpenCV
- PostgreSQL en produccion, SQLite en desarrollo
- Desplegado en DigitalOcean App Platform (URL: checador-loginco-app-zd3ie.ondigitalocean.app)

## Apps del Proyecto
authentication | empleados | horarios | registros | organizacion | permisos | visitas | reportes | it_tickets

## Patrones Criticos

### Resolucion de Horarios (cascada de 3 prioridades)
1. AsignacionHorario especifica (fecha exacta) -> prioridad maxima
2. Horario semanal (por dia_semana) -> prioridad media
3. horario_predeterminado/sabado/domingo en Empleado -> prioridad minima
Funcion: `horarios.services.obtener_horario_del_dia(empleado, fecha)`

### Encoding Facial
- Se guarda en `Empleado.embedding_rostro` (BinaryField) usando `pickle.dumps(numpy_array)`
- Se recupera con `empleado.get_face_encoding()` -> `pickle.loads()` -> numpy array 128-dim
- RIESGO DE SEGURIDAD: pickle es vulnerable si la DB es comprometida. Alternativa segura: JSON list de floats.

### Endpoints AllowAny (Kiosko)
- `/api/registros/marcar_entrada/`, `/marcar_salida/`, `/marcar_salida_comida/`, `/marcar_entrada_comida/`, `/verificar_rostro/` son publicos
- Justificacion: kiosko fisico compartido, la autenticacion es biometrica

### Zona Horaria
- MEXICO_TZ = ZoneInfo('America/Mexico_City') importado en models.py y views.py de registros
- Siempre convertir: `timezone.now().astimezone(MEXICO_TZ)`
- DB almacena UTC, la conversion es en capa de aplicacion

### Doble Canal de Autenticacion
- Sesiones Django: dashboard, empleados, horarios, permisos, visitas
- JWT Bearer: API REST
- Para registro facial desde web: endpoints `-session/` que usan `request.user` de sesion

## Deuda Tecnica Conocida
- Scan lineal en recognize_employee(): O(N) empleados. Soluciones: FAISS, pgvector, cache Redis
- Señales globales en storage_backends.py sin sender especifico (performance)
- Campo `departamento` (CharField) duplicado con `departamento_obj` (FK) en Empleado
- APScheduler en proceso web -> problema con multiples workers. Solucion: Celery + Celery Beat
- RegistroAsistencia sin indice en campo `fecha` individual (solo unique_together con empleado)

## Archivos Clave
- `/home/tony/Developer/ChecadorLogincoV2/context.md` - Analisis exhaustivo completo del proyecto
- `checador/settings.py` - Configuracion, manejo de USE_SPACES, DATABASE_URL
- `checador/storage_backends.py` - Backends S3 y señales de limpieza de archivos
- `horarios/services.py` - Funcion unica de resolucion de horario
- `registros/services/facial_recognition.py` - FacialRecognitionService (todo estatico)
- `registros/models.py` - Maquina de estados en obtener_botones_disponibles()
- `reportes/scheduler.py` - APScheduler jobs para reportes automaticos

## App it_tickets (agregada 2026-02-27)
- Modelos: EquipoComputo, Ticket (folio TKT-YYYYMMDD-XXX), HistorialTicket, MantenimientoEquipo
- Ciclo de vida ticket: creado -> pendiente -> proceso -> espera -> concluido
- Permiso de acceso: grupo Django 'IT' (creado en migración 0001_initial via RunPython)
- Señales en models.py (patron del proyecto): pre_save captura estado anterior, post_save dispara emails
- Scheduler: it_tickets/scheduler.py arrancado desde ItTicketsConfig.ready() (mismo patron que reportes)
- Management command: `python manage.py importar_inventario_csv <ruta.csv> [--actualizar] [--dry-run]`
- URLs: path('', include('it_tickets.urls', namespace='it_tickets')) en checador/urls.py
  - API: /api/it/equipos/, /api/it/tickets/, /api/it/mantenimientos/
  - Web: /it/, /it/tickets/, /it/inventario/, /it/mantenimiento/calendario/
- Dependencia de migración: empleados/0004_...

## Notas de Deployment
- Procfile: gunicorn 2 workers, puerto 8080, timeout 120s
- app.yaml: DigitalOcean App Platform, basic-xxs, PostgreSQL 16
- Health check: /admin/login/
- Deploy automatico en push a main
- dlib requiere paquetes del SO (ver Aptfile y DLIB_FIX.md)
