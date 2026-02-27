# Context: ChecadorLogincoV2

Sistema de Control de Asistencias con reconocimiento facial para Loginco. Construido con Django 6.0, Django REST Framework, y reconocimiento biométrico via face_recognition/OpenCV. Desplegado en DigitalOcean App Platform con PostgreSQL 16.

---

## 1. Estructura del Proyecto

```
ChecadorLogincoV2/
├── checador/                  # Configuracion central del proyecto
│   ├── settings.py            # Configuracion principal
│   ├── urls.py                # URL dispatcher principal
│   ├── views.py               # Vistas web (login, dashboard, empleados, registros)
│   ├── storage_backends.py    # Backends de almacenamiento S3/Spaces + señales
│   ├── wsgi.py
│   └── asgi.py
├── authentication/            # JWT auth (registro, login, logout, cambio contraseña)
├── empleados/                 # Gestion de empleados y embeddings faciales
├── horarios/                  # Plantillas y asignacion de horarios
├── registros/                 # Registros de asistencia y servicio facial
│   └── services/
│       └── facial_recognition.py   # FacialRecognitionService
├── organizacion/              # Estructura organizacional (departamentos, supervision)
├── permisos/                  # Solicitudes de permiso laboral con historial
├── visitas/                   # Control de visitas con QR
├── reportes/                  # Generacion y envio automatico de reportes
│   ├── scheduler.py           # APScheduler (cron interno de Django)
│   └── services/
│       ├── calculos.py        # Calculo de datos de asistencia para reportes
│       ├── generador_excel.py # Generacion de archivos Excel
│       └── generador_email.py # Envio de reportes por email via SendGrid
├── templates/                 # Templates HTML (Tailwind CSS + FontAwesome)
│   ├── auth/
│   ├── empleados/
│   ├── horarios/
│   ├── permisos/
│   ├── registros/
│   ├── visitas/
│   ├── organizacion/
│   ├── reportes/email/
│   ├── facial_recognition.html
│   ├── facial_recognition_comida.html
│   ├── register_face.html
│   ├── register_face_standalone.html
│   ├── dashboard.html
│   └── base.html
├── requirements.txt
├── Procfile                   # gunicorn 2 workers, puerto 8080
├── Dockerfile
├── app.yaml                   # DigitalOcean App Platform config
├── build.sh
├── runtime.txt
└── .env.example
```

---

## 2. Stack Tecnologico

### Dependencias Principales

| Paquete | Version | Proposito |
|---|---|---|
| Django | 6.0 | Framework principal |
| djangorestframework | 3.16.1 | API REST |
| djangorestframework_simplejwt | 5.5.1 | Autenticacion JWT |
| django-cors-headers | 4.9.0 | CORS para clientes externos |
| django-storages | 1.14.6 | Backend S3 para DigitalOcean Spaces |
| face-recognition | 1.3.0 | Deteccion y comparacion facial (wraps dlib) |
| opencv-python-headless | 4.10.0.84 | Procesamiento de imagenes |
| numpy | 2.2.6 | Arrays numericos para encodings |
| Pillow | 12.0.0 | Manejo de imagenes |
| psycopg2-binary | 2.9.11 | Driver PostgreSQL |
| mysqlclient | 2.2.7 | Driver MySQL (alternativa) |
| dj-database-url | 3.0.1 | Parseo DATABASE_URL para produccion |
| gunicorn | 23.0.0 | Servidor WSGI produccion |
| whitenoise | 6.8.2 | Servicio de archivos estaticos |
| django-apscheduler | 0.6.2 | Scheduler interno (reemplaza cron del SO) |
| qrcode[pil] | 7.4.2 | Generacion de codigos QR para visitas |
| openpyxl | 3.1.5 | Generacion de reportes Excel |
| reportlab | 4.4.7 | Generacion de PDF (disponible, sin uso actual) |
| python-decouple | 3.8 | Gestion de variables de entorno |
| boto3 | 1.41.5 | SDK AWS/Spaces |

---

## 3. Configuracion (settings.py)

### Base de Datos
- **Desarrollo**: SQLite (`db.sqlite3`)
- **Produccion**: PostgreSQL via `DATABASE_URL` con `dj-database-url`, SSL requerido (`sslmode=require`)
- **Alternativa**: MySQL soportado con charset utf8mb4

### Autenticacion y Seguridad
- Autenticacion dual: sesiones Django (web) + JWT Bearer tokens (API)
- JWT: access token 60 min, refresh token 1440 min (24h), blacklist activado
- Token blacklist habilitado (`rest_framework_simplejwt.token_blacklist`)
- HSTS activado en produccion (31536000 segundos con subdomains y preload)
- `SECURE_SSL_REDIRECT = True` en produccion

### Internacionalizacion
- `LANGUAGE_CODE = 'es-mx'`
- `TIME_ZONE = 'America/Mexico_City'`
- `USE_TZ = True` (timestamps UTC en DB, conversion a Mexico en vistas)

### Almacenamiento de Archivos
- **Desarrollo**: sistema de archivos local, servido por WhiteNoise
- **Produccion** (`USE_SPACES=True`): DigitalOcean Spaces (S3-compatible) via `django-storages`
  - Estaticos: bucket/static/ con ACL public-read
  - Media: bucket/media/ con ACL public-read
  - Reportes: bucket/reportes/ con ACL private
  - Soporte CDN via `DO_SPACES_CDN_ENDPOINT`

### REST Framework
- Autenticacion default: JWT
- Permiso default: `IsAuthenticated`
- Paginacion: `PageNumberPagination` con `PAGE_SIZE=20`
- Filtros: `SearchFilter` y `OrderingFilter`

### Email
- Backend SMTP via SendGrid (`smtp.sendgrid.net:587`, TLS)
- Variable `SENDGRID_API_KEY` requerida en produccion

### Scheduler
- `django-apscheduler` con `BackgroundScheduler`
- Se inicia automaticamente en `ReportesConfig.ready()` solo en `runserver` y `gunicorn`
- Jobs persistidos en DB via `DjangoJobStore`

---

## 4. Modelos de Base de Datos

### App: authentication
No define modelos propios. Usa `django.contrib.auth.models.User` directamente.

### App: empleados

#### Empleado
Extiende el `User` de Django via relacion `OneToOneField`.

| Campo | Tipo | Descripcion |
|---|---|---|
| user | OneToOneField(User) | Usuario Django asociado (CASCADE) |
| codigo_empleado | CharField(20, unique) | Identificador interno del empleado |
| foto_rostro | ImageField | Foto de referencia almacenada en Spaces/local |
| embedding_rostro | BinaryField | Numpy array serializado con pickle (encoding facial dlib de 128 dimensiones) |
| horas_semana | IntegerField(default=40) | Horas laborales semanales |
| departamento | CharField(100) | Nombre textual del departamento (legacy) |
| departamento_obj | FK(organizacion.Departamento, SET_NULL) | Relacion estructural al departamento |
| supervisor_directo | FK('self', SET_NULL) | Auto-referencia para jerarquia directa |
| puesto | CharField(100, blank) | Cargo del empleado |
| fecha_ingreso | DateField(null) | Fecha de inicio en la empresa |
| horario_predeterminado | FK(TipoHorario, SET_NULL) | Horario Lun-Vie por defecto |
| horario_sabado | FK(TipoHorario, SET_NULL) | Horario sabados (opcional) |
| descansa_sabado | BooleanField(default=False) | Flag de descanso en sabado |
| horario_domingo | FK(TipoHorario, SET_NULL) | Horario domingos (opcional) |
| descansa_domingo | BooleanField(default=True) | Flag de descanso en domingo |
| activo | BooleanField(default=True) | Soft-delete de empleados |
| fecha_creacion | DateTimeField(auto_now_add) | |
| fecha_actualizacion | DateTimeField(auto_now) | |

Metodos relevantes:
- `set_face_encoding(array)`: serializa con `pickle.dumps()` y guarda en `embedding_rostro`
- `get_face_encoding()`: deserializa con `pickle.loads()` y retorna numpy array
- `tiene_rostro_registrado` (property): bool
- `nombre_completo` (property): `first_name + last_name` o username
- `eliminar_rostro()`: limpia embedding y elimina foto del storage
- `get_supervisores()`: resuelve lista de supervisores aplicando tres fuentes (supervisor_directo, RelacionSupervision activas, responsable del departamento)

### App: horarios

#### TipoHorario
Plantilla de horario reutilizable y nombrada.

| Campo | Tipo | Descripcion |
|---|---|---|
| nombre | CharField(100, unique) | Nombre descriptivo (ej: "Turno Matutino") |
| codigo | CharField(20, unique) | Codigo corto (ej: "MAT") |
| descripcion | TextField | Descripcion libre |
| color | CharField(7) | Color hex para UI de asignacion |
| hora_entrada | TimeField | Hora de inicio de turno |
| hora_salida | TimeField | Hora de fin de turno |
| tolerancia_minutos | IntegerField(default=10) | Minutos de gracia para entrada |
| tiene_comida | BooleanField(default=True) | Si el turno incluye periodo de comida |
| hora_inicio_comida | TimeField(null) | Desde cuando puede salir a comer |
| hora_fin_comida | TimeField(null) | Limite para regresar de comer |
| activo | BooleanField | |

Metodo: `esta_en_horario_comida(hora_actual)` retorna bool.

#### AsignacionHorario
Asignacion especifica de un TipoHorario a un empleado en una fecha concreta. Tiene prioridad maxima en la resolucion de horarios.

| Campo | Tipo | Descripcion |
|---|---|---|
| empleado | FK(Empleado, CASCADE) | |
| fecha | DateField | Fecha especifica de la asignacion |
| tipo_horario | FK(TipoHorario, CASCADE) | Horario asignado |
| notas | CharField(255, blank) | Notas opcionales |
| creado_por | FK(User, SET_NULL) | Quien realizo la asignacion |

Restricciones: `unique_together = ['empleado', 'fecha']`. Indices en `fecha` y `(empleado, fecha)`.

#### Horario
Definicion de horario por dia de semana para un empleado (modelo legacy, prioridad secundaria).

| Campo | Tipo | Descripcion |
|---|---|---|
| empleado | FK(Empleado, CASCADE) | |
| dia_semana | IntegerField(choices 1-7) | 1=Lunes, 7=Domingo |
| hora_entrada | TimeField | |
| hora_salida | TimeField | |
| tiene_comida | BooleanField | |
| hora_inicio_comida | TimeField(null) | |
| hora_fin_comida | TimeField(null) | |
| tolerancia_minutos | IntegerField(default=10) | |
| activo | BooleanField | |

Restricciones: `unique_together = ['empleado', 'dia_semana']`.

Property `horas_dia`: calcula horas efectivas descontando tiempo de comida.

### App: registros

#### RegistroAsistencia
Registro diario de asistencia. Un registro por empleado por dia (`unique_together`). Guarda los cuatro puntos de control del dia.

| Campo | Tipo | Descripcion |
|---|---|---|
| empleado | FK(Empleado, CASCADE) | |
| fecha | DateField(default=fecha_mexico) | Fecha en zona horaria Mexico |
| hora_entrada | TimeField(null) | Punto de control: llegada |
| hora_salida_comida | TimeField(null) | Punto de control: salida a comer |
| hora_entrada_comida | TimeField(null) | Punto de control: regreso de comer |
| hora_salida | TimeField(null) | Punto de control: salida final |
| horas_trabajadas | FloatField(default=0) | Calculado automaticamente en save() |
| reconocimiento_facial | BooleanField | Si se uso biometria |
| foto_registro | ImageField | Foto tomada en el momento del registro |
| confianza_reconocimiento | FloatField(null) | Porcentaje de confianza del match facial |
| ubicacion | CharField(255, blank) | Descripcion textual de ubicacion |
| latitud | DecimalField(9,6, null) | GPS |
| longitud | DecimalField(9,6, null) | GPS |
| retardo | BooleanField(default=False) | Calculado automaticamente |
| justificado | BooleanField(default=False) | Eximir de incidencia |
| incidencia | CharField(choices) | ninguna, registro_incompleto, sin_entrada_comida, sin_salida_comida, sin_salida |
| descripcion_incidencia | TextField | Mensaje descriptivo de la incidencia |
| notas | TextField | Notas manuales |

Logica en `save()`:
- Si tiene `hora_entrada` y `hora_salida`: llama `calcular_horas_trabajadas()` (descuenta comida si hay registro completo de comida)
- Si tiene `hora_entrada`: llama `verificar_retardo()` usando `horarios.services.obtener_horario_del_dia`

Metodo `obtener_botones_disponibles(hora_actual)`: maquina de estados que retorna lista de acciones disponibles segun el flujo actual del registro. Estados: `['entrada']` -> `['salida_comida', 'salida']` -> `['entrada_comida']` -> `['salida']` -> `[]`.

Metodo `calcular_incidencias()`: determina el tipo de incidencia basado en el estado actual del registro. Ejecutado por el management command `detectar_incidencias`.

### App: organizacion

#### Departamento
Estructura organizacional jerarquica (arbol n-ario via auto-FK).

| Campo | Tipo | Descripcion |
|---|---|---|
| nombre | CharField(100, unique) | |
| codigo | CharField(20, unique) | |
| descripcion | TextField | |
| departamento_padre | FK('self', SET_NULL) | Para jerarquia de departamentos |
| responsable | FK(Empleado, SET_NULL) | Empleado a cargo del departamento |
| activo | BooleanField | |

Metodos: `get_nivel()`, `get_ruta()`, `get_subordinados_directos()`, `get_todos_subordinados()` (recursivo).

#### RelacionSupervision
Define relaciones de supervision entre empleados con tipos y vigencia.

| Campo | Tipo | Descripcion |
|---|---|---|
| supervisor | FK(Empleado, CASCADE) | |
| subordinado | FK(Empleado, CASCADE) | |
| tipo_relacion | CharField(choices) | directa, funcional, temporal |
| puede_autorizar_permisos | BooleanField(default=True) | Si este supervisor puede aprobar permisos |
| fecha_inicio | DateField | |
| fecha_fin | DateField(null) | Null = sin fecha de fin |
| activo | BooleanField | |

Restriccion: `unique_together = ['supervisor', 'subordinado', 'tipo_relacion']`.

Metodo `esta_vigente()`: verifica activo, fecha_inicio <= hoy, y que fecha_fin no haya pasado.

### App: permisos

#### TipoPermiso
Catalogo de tipos de permiso laboral.

| Campo | Tipo | Descripcion |
|---|---|---|
| nombre | CharField(100) | |
| codigo | CharField(10, unique) | |
| descripcion | TextField | |
| requiere_evidencia | BooleanField | Si es obligatorio adjuntar documento |
| dias_maximos | IntegerField(null) | Limite de dias por solicitud |
| dias_anticipacion | IntegerField(default=1) | Con cuantos dias de anticipacion solicitar |
| afecta_salario | BooleanField(default=True) | Con goce de sueldo |
| color | CharField(7) | Color hex para UI |
| activo | BooleanField | |

#### SolicitudPermiso
Solicitud de permiso con flujo de estados y auditoria.

| Campo | Tipo | Descripcion |
|---|---|---|
| empleado | FK(Empleado, CASCADE) | Solicitante |
| tipo_permiso | FK(TipoPermiso, PROTECT) | Tipo de permiso solicitado |
| fecha_inicio | DateField | Inicio del periodo solicitado |
| fecha_fin | DateField | Fin del periodo solicitado |
| hora_inicio | TimeField(null) | Para permisos por horas |
| hora_fin | TimeField(null) | Para permisos por horas |
| motivo | TextField | Justificacion libre |
| evidencia | FileField | Documento adjunto (en Spaces/local) |
| estado | CharField(choices) | borrador, pendiente, aprobado, rechazado, cancelado |
| aprobador | FK(Empleado, SET_NULL) | Quien resolvio la solicitud |
| fecha_resolucion | DateTimeField(null) | |
| comentarios_resolucion | TextField | |

Properties: `dias_solicitados`, `es_por_horas`.

Metodos de transicion de estado: `aprobar()`, `rechazar()`, `cancelar()`, `enviar()`. Cada uno crea un registro en `HistorialPermiso`.

Metodo `puede_ser_aprobado_por(empleado)`: verifica en tres niveles (RelacionSupervision vigente, responsable del departamento, is_staff).

#### HistorialPermiso
Auditoria de cada cambio de estado en una solicitud.

| Campo | Tipo | Descripcion |
|---|---|---|
| solicitud | FK(SolicitudPermiso, CASCADE) | |
| accion | CharField(choices) | creado, enviado, aprobado, rechazado, cancelado, modificado |
| usuario | FK(Empleado, SET_NULL) | Quien ejecuto la accion |
| comentarios | TextField | |
| fecha | DateTimeField(auto_now_add) | |

### App: visitas

#### MotivoVisita
Catalogo de motivos de visita.

| Campo | Tipo |
|---|---|
| nombre | CharField(100) |
| descripcion | TextField |
| requiere_autorizacion | BooleanField(default=True) |
| activo | BooleanField |

#### Visita
Control completo de visitantes con QR y estados.

| Campo | Tipo | Descripcion |
|---|---|---|
| codigo_visita | UUIDField(auto, unique) | Identificador para QR |
| nombre_visitante | CharField(200) | |
| empresa | CharField(200, blank) | |
| email | EmailField(blank) | |
| telefono | CharField(20, blank) | |
| identificacion_tipo | CharField(choices) | ine, pasaporte, licencia, otro |
| identificacion_numero | CharField(50, blank) | |
| foto_visitante | ImageField | Foto del visitante (Spaces) |
| foto_identificacion | ImageField | Foto del documento (Spaces) |
| motivo | TextField | Motivo de la visita |
| departamento_destino | FK(Departamento, SET_NULL) | |
| fecha_programada | DateField | |
| hora_programada | TimeField | |
| duracion_estimada | IntegerField(default=60) | Minutos |
| fecha_entrada | DateTimeField(null) | Registro real de entrada |
| fecha_salida | DateTimeField(null) | Registro real de salida |
| codigo_qr | ImageField | Imagen QR generada (Spaces) |
| estado | CharField(choices) | pendiente, autorizado, en_sitio, finalizado, rechazado, cancelado, no_show |
| autorizado_por | FK(Empleado, SET_NULL) | |
| fecha_autorizacion | DateTimeField(null) | |
| comentarios_autorizacion | TextField | |

Metodo `generar_qr()`: usa libreria `qrcode` para crear imagen PNG con el UUID, la guarda en Spaces.

Metodos de transicion: `autorizar()`, `rechazar()`, `registrar_entrada()`, `registrar_salida()`, `cancelar()`, `marcar_no_show()`.

Property `codigo_corto`: primeros 8 caracteres del UUID en mayusculas.

### App: reportes

#### ConfiguracionReporte
Configuracion global por tipo de reporte.

| Campo | Tipo | Descripcion |
|---|---|---|
| tipo | CharField(unique choices) | diario, semanal, quincenal |
| activo | BooleanField | |
| hora_envio | TimeField(default=11:50) | Hora de envio diario |
| asunto_email | CharField(255, blank) | Asunto personalizado |
| dia_envio_semanal | IntegerField(null, choices) | 5=Viernes, 6=Sabado |
| incluir_excel | BooleanField | Si adjunta Excel al email |

#### DestinatarioReporte
Lista de destinatarios por configuracion.

| Campo | Tipo |
|---|---|
| configuracion | FK(ConfiguracionReporte, CASCADE) |
| nombre | CharField(100) |
| email | EmailField |
| activo | BooleanField |

Restriccion: `unique_together = ['configuracion', 'email']`.

#### LogReporte
Auditoria de cada envio de reporte.

| Campo | Tipo | Descripcion |
|---|---|---|
| tipo_reporte | CharField(20) | |
| fecha_inicio_rango | DateField | |
| fecha_fin_rango | DateField | |
| destinatarios_enviados | IntegerField | |
| estado | CharField(choices) | enviado, error, parcial |
| error_detalle | TextField | Para estado error |
| fecha_envio | DateTimeField(auto_now_add) | |

---

## 5. APIs REST

### Base URL: `/api/`

### Autenticacion: `/api/auth/`

| Endpoint | Metodo | Permiso | Descripcion |
|---|---|---|---|
| `/api/auth/login/` | POST | AllowAny | Obtener JWT access + refresh tokens |
| `/api/auth/token/refresh/` | POST | AllowAny | Renovar access token con refresh token |
| `/api/auth/register/` | POST | AllowAny | Crear usuario, retorna tokens JWT |
| `/api/auth/logout/` | POST | IsAuthenticated | Blacklist del refresh token |
| `/api/auth/profile/` | GET/PATCH | IsAuthenticated | Ver y actualizar perfil del usuario autenticado |
| `/api/auth/change-password/` | PUT | IsAuthenticated | Cambiar contraseña (requiere old_password) |

### Empleados: `/api/empleados/`

Router DefaultRouter, todas las rutas con `IsAuthenticated`.

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/empleados/` | GET | Listar empleados (filtros: activo, departamento, search) |
| `/api/empleados/` | POST | Crear empleado + usuario Django en una operacion |
| `/api/empleados/{id}/` | GET | Detalle completo del empleado |
| `/api/empleados/{id}/` | PUT/PATCH | Actualizar empleado y datos del usuario |
| `/api/empleados/{id}/` | DELETE | Eliminar empleado |
| `/api/empleados/{id}/registrar-rostro/` | POST | Registrar encoding facial (foto en multipart) |
| `/api/empleados/{id}/eliminar-rostro/` | POST | Eliminar encoding y foto facial |

Serializers diferenciados por accion: `EmpleadoListSerializer` (lista), `EmpleadoDetailSerializer` (detalle), `EmpleadoCreateSerializer` (creacion con campos de User), `EmpleadoUpdateSerializer` (actualizacion parcial de User y Empleado), `RegistrarRostroSerializer` (solo foto_rostro, validacion max 5MB).

### Horarios: `/api/horarios/`

Router DefaultRouter con tres ViewSets.

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/horarios/` | GET/POST | CRUD de Horarios (por dia de semana) |
| `/api/horarios/{id}/` | GET/PUT/PATCH/DELETE | Horario individual |
| `/api/horarios/bulk-create/` | POST | Crear multiples horarios para un empleado |
| `/api/horarios/tipos/` | GET/POST | CRUD de TipoHorario (plantillas) |
| `/api/horarios/tipos/{id}/` | GET/PUT/PATCH/DELETE | TipoHorario individual |
| `/api/horarios/asignaciones/` | GET/POST | CRUD de AsignacionHorario |
| `/api/horarios/asignaciones/{id}/` | GET/PUT/PATCH/DELETE | Asignacion individual |
| `/api/horarios/asignaciones/asignar/` | POST | Upsert de asignacion (o DELETE si tipo_horario=0) |
| `/api/horarios/asignaciones/bulk/` | POST | Asignar un tipo a multiples empleados/fechas |

Filtros disponibles: `empleado`, `dia_semana`, `activo` (en Horario); `activo` (en TipoHorario); `empleado`, `mes`, `anio`, `fecha` (en AsignacionHorario).

### Registros: `/api/registros/`

Router DefaultRouter, mixtura de permisos.

| Endpoint | Metodo | Permiso | Descripcion |
|---|---|---|---|
| `/api/registros/` | GET | IsAuthenticated | Listar registros (filtros: empleado, fecha, fecha_inicio, fecha_fin) |
| `/api/registros/` | POST | IsAuthenticated | Crear registro manual |
| `/api/registros/{id}/` | GET/PUT/PATCH/DELETE | IsAuthenticated | CRUD individual |
| `/api/registros/marcar_entrada/` | POST | **AllowAny** | Marcar entrada via reconocimiento facial |
| `/api/registros/marcar_salida/` | POST | **AllowAny** | Marcar salida via reconocimiento facial |
| `/api/registros/marcar_salida_comida/` | POST | **AllowAny** | Marcar salida a comer |
| `/api/registros/marcar_entrada_comida/` | POST | **AllowAny** | Marcar regreso de comer |
| `/api/registros/verificar_rostro/` | POST | **AllowAny** | Verificar identidad y retornar estado sin marcar asistencia |

Nota de seguridad: los endpoints de marcacion son `AllowAny` porque la pantalla del checador es un kiosko publico que no tiene sesion de usuario. La "autenticacion" en este caso es el reconocimiento facial en si mismo.

### Organizacion: `/api/organizacion/`

CRUD de `Departamento` y `RelacionSupervision`.

### Permisos: `/api/permisos/`

CRUD de `TipoPermiso`, `SolicitudPermiso`, y acciones de transicion de estado.

### Visitas: `/api/visitas/`

CRUD de `MotivoVisita` y `Visita`, incluyendo verificacion de QR.

---

## 6. Vistas Web (No-API)

Todas las vistas web usan autenticacion por sesion Django (cookies).

| URL | Vista | Permiso | Descripcion |
|---|---|---|---|
| `/` y `/facial/` | `facial_recognition_page` | AllowAny | Kiosko de reconocimiento facial (entrada/salida) |
| `/checador/` | `facial_recognition_comida_page` | AllowAny | Kiosko con control de comida |
| `/login/` | `login_view` | AllowAny | Formulario de inicio de sesion |
| `/register/` | `register_view` | AllowAny | Formulario de registro de empleado |
| `/logout/` | `logout_view` | Sesion | Cierre de sesion |
| `/dashboard/` | `dashboard_view` | `@login_required` | Dashboard con metricas del dia y mes |
| `/empleados/` | `empleados_lista_view` | `@login_required + is_staff` | Lista de empleados con busqueda |
| `/registros/` | `registros_lista_view` | `@login_required + is_staff` | Lista de registros con filtros y estadisticas |
| `/marcar-asistencia/` | `marcar_asistencia_view` | `@login_required` | Redirige a `/facial/` |
| `/horarios/asignacion/` | `asignacion_horarios_view` | sesion | Vista de calendario para asignar horarios |
| `/organigrama/` | `organigrama_view` | sesion | Arbol de la estructura organizacional |
| `/mis-permisos/` | `mis_permisos_view` | sesion | Permisos del empleado autenticado |
| `/permisos/nueva/` | `nueva_solicitud_view` | sesion | Formulario de nueva solicitud de permiso |
| `/permisos/{pk}/` | `detalle_permiso_view` | sesion | Detalle de un permiso |
| `/permisos/aprobar/` | `aprobar_permisos_view` | sesion + supervisor | Lista de permisos pendientes de aprobacion |
| `/permisos/{pk}/{accion}/` | `accion_permiso_view` | sesion | Ejecutar accion en permiso |
| `/visitas/registrar/` | `registrar_visita_view` | AllowAny | Formulario publico de registro de visita |
| `/visitas/verificar/` | `verificar_qr_view` | sesion | Formulario para ingresar codigo QR |
| `/visitas/verificar/{uuid}/` | `verificar_resultado_view` | sesion | Resultado de verificacion y acciones |
| `/visitas/` | `lista_visitas_view` | sesion | Lista de visitas del dia |
| `/visitas/{pk}/` | `detalle_visita_view` | sesion | Detalle de visita |
| `/visitas/{pk}/{accion}/` | `accion_visita_view` | sesion | Ejecutar accion en visita |
| `/empleados/{id}/registrar-rostro-web/` | `register_face_view` | `@login_required` | Template de camara para registrar rostro |
| `/empleados/{id}/registrar-rostro-session/` | `register_face_post` | `@login_required` | POST para guardar rostro via sesion |
| `/empleados/{id}/eliminar-rostro-session/` | `delete_face_post` | `@login_required + is_staff` | POST para eliminar rostro via sesion |

### Dashboard (`/dashboard/`)
Contenido segun el tipo de usuario:

- **Empleado regular**: registro de hoy (entrada/salida), dias trabajados en el mes, retardos del mes, horas totales del mes, ultimos 7 registros, permisos recientes, conteo de permisos pendientes propios.
- **Staff adicional**: total de empleados activos, registros de hoy, empleados sin rostro registrado, permisos pendientes de aprobar, visitas del dia (total, pendientes, en sitio).

---

## 7. Servicio de Reconocimiento Facial

### `FacialRecognitionService` (`registros/services/facial_recognition.py`)

Clase de utilidades estaticas (todos los metodos son `@staticmethod`).

#### Configuracion
```python
FACE_TOLERANCE = 0.6   # Distancia maxima para considerar coincidencia
MIN_FACE_SIZE = (50, 50)  # Tamano minimo del rostro en pixeles
MAX_FACES_ALLOWED = 1  # Solo se acepta un rostro por imagen
```

#### Flujo de Registro de Rostro
```
1. load_image_from_file(image_file)
   - Si es InMemoryUploadedFile: PIL.Image -> numpy RGB array
   - Si es path: face_recognition.load_image_file()

2. validate_image_quality(image)
   - Verifica dimensiones minimas (100x100)
   - Verifica brillo (30 < mean_brightness < 225) via OpenCV
   - Verifica nitidez (Laplacian variance > 100) via OpenCV

3. extract_face_encoding(image, validate=True)
   - Detecta ubicaciones de rostros via face_recognition.face_locations()
   - Verifica: exactamente 1 rostro, tamano >= MIN_FACE_SIZE
   - Extrae encoding via face_recognition.face_encodings()
   - Retorna numpy array de 128 dimensiones (dlib ResNet)

4. empleado.set_face_encoding(encoding)
   - Serializa con pickle.dumps()
   - Guarda en BinaryField
```

#### Flujo de Reconocimiento (Marcacion de Asistencia)
```
1. load_image_from_file(foto_capturada)

2. recognize_employee(image)
   a. extract_face_encoding() de la imagen capturada
   b. SELECT empleados activos con embedding_rostro IS NOT NULL
   c. Para cada empleado:
      - get_face_encoding() -> deserializa pickle
      - compare_faces(known, unknown):
          * face_distance() -> float 0-1
          * confidence = (1 - distance) * 100
          * compare_faces(tolerance=0.6) -> bool
   d. Retorna el empleado con mayor confianza que supere la tolerancia

3. RegistroAsistencia.objects.get_or_create(empleado=emp, fecha=hoy)

4. Segun tipo (entrada/salida_comida/entrada_comida/salida):
   - Valida que el estado anterior sea correcto (maquina de estados)
   - Actualiza el campo de hora correspondiente
   - Guarda foto del registro

5. registro.save() -> calcula horas_trabajadas y verifica retardo automaticamente
```

#### Consideraciones de Rendimiento
El metodo `recognize_employee()` hace un scan lineal de **todos** los empleados activos con rostro registrado. Para N empleados, se ejecutan N comparaciones de vectores de 128 dimensiones. Con decenas de empleados esto es aceptable; con cientos podria ser lento y requerira optimizacion (FAISS, pgvector, etc.).

---

## 8. Servicio de Resolucion de Horarios

### `obtener_horario_del_dia(empleado, fecha)` (`horarios/services.py`)

Implementa una cascada de tres prioridades para determinar el horario aplicable:

1. **AsignacionHorario especifica**: busca `AsignacionHorario` exacto para `(empleado, fecha)`. Prioridad maxima.
2. **Horario semanal**: busca en `Horario` con el `dia_semana` correspondiente a la fecha (via `isoweekday()`).
3. **Horario predeterminado del Empleado**:
   - Sabado (dia 6): si `descansa_sabado=True` retorna `None`, sino usa `horario_sabado`
   - Domingo (dia 7): si `descansa_domingo=True` retorna `None`, sino usa `horario_domingo`
   - Lun-Vie (1-5): usa `horario_predeterminado`

Retorna un diccionario normalizado con: `hora_entrada`, `hora_salida`, `tolerancia_minutos`, `tiene_comida`, `hora_inicio_comida`, `hora_fin_comida`, `nombre`, `fuente` (para debugging), `objeto` (instancia del modelo fuente).

Retorna `None` si el empleado no labora ese dia o no tiene horario configurado.

---

## 9. Almacenamiento de Archivos (storage_backends.py)

### Clases de Storage

| Clase | Location | ACL | file_overwrite | Uso |
|---|---|---|---|---|
| `StaticStorage` | static/ | public-read | True | Archivos CSS/JS (collectstatic) |
| `MediaStorage` | media/ | public-read | False | Fotos de rostros y asistencias |
| `ReportesStorage` | reportes/ | private | True | Archivos Excel de reportes |
| `SecureMediaStorage` | media/ | private | False | Archivos que requieren URL firmada (1h) |

`MediaStorage._save()` agrega un timestamp en hora Mexico al nombre del archivo para evitar colisiones.

### Señales Automaticas
- `post_delete`: elimina archivos del storage cuando se elimina una instancia de modelo
- `pre_save`: elimina el archivo anterior cuando un campo de archivo es actualizado

Nota: estas señales son globales (`@receiver(post_delete)` sin sender especifico), lo que significa que se ejecutan para **todos** los modelos con campos de archivo. Esto puede generar llamadas innecesarias al storage.

---

## 10. Sistema de Reportes Automaticos

### Scheduler (`reportes/scheduler.py`)
Usa `APScheduler` con `BackgroundScheduler` (hilo daemon) y persistencia en DB via `DjangoJobStore`.

Se inicia automaticamente en `ReportesConfig.ready()` solo cuando se detecta `runserver` o `gunicorn` en `sys.argv`, y solo en el proceso principal (no en el reloader de runserver).

| Job | Trigger | Descripcion |
|---|---|---|
| `reporte_diario` | Lun-Sab 11:50am | Reporte de asistencia del dia |
| `reporte_semanal` | Viernes 11:50am | Reporte Lunes-Viernes de la semana actual |
| `reporte_quincenal` | Dias 14 y 29 11:50am | Reporte de la quincena correspondiente |
| `delete_old_job_executions` | Diario 00:00am | Limpia ejecuciones > 7 dias de la DB |

### Flujo de Reporte
```
1. ConfiguracionReporte.objects.get(tipo=X, activo=True)
2. destinatarios = configuracion.destinatarios.filter(activo=True)
3. obtener_datos_reporte(fecha_inicio, fecha_fin)
   - Carga empleados activos con select_related
   - Carga registros del rango
   - Calcula: dias_trabajados, retardos, faltas, horas_totales por empleado
   - Genera: top_5_retardos, empleados_con_faltas
4. generar_reporte_excel(datos) -> BytesIO con openpyxl
5. enviar_reporte(tipo, datos, destinatarios, excel) via SendGrid SMTP
6. LogReporte.objects.create(estado='enviado'|'error')
```

### Management Commands de Reportes
- `python manage.py enviar_reporte` - Envio manual de reportes
- `python manage.py detectar_incidencias [--fecha YYYY-MM-DD]` - Revisa registros del dia anterior y marca incidencias

---

## 11. Autenticacion Dual

El sistema implementa dos mecanismos paralelos de autenticacion:

### Sesiones Django (Web)
- Login en `/login/` con `authenticate()` + `login()`
- `@login_required` y `@user_passes_test(lambda u: u.is_staff)` en vistas web
- Usado para el dashboard, administracion de empleados, horarios, permisos, visitas

### JWT (API REST)
- Bearer tokens via `djangorestframework-simplejwt`
- `IsAuthenticated` con `JWTAuthentication` como default en REST_FRAMEWORK
- Access token: 60 min | Refresh token: 24h
- Blacklist activado: logout invalida el refresh token permanentemente
- Rotacion: al refrescar, el refresh token anterior queda en blacklist

### Endpoints AllowAny (Kiosko)
Los endpoints de marcacion de asistencia son publicos porque:
- La pantalla del checador es un kiosko fisico compartido
- La autenticacion del empleado se realiza mediante reconocimiento facial biometrico
- No hay sesion de usuario en el kiosko

---

## 12. Templates y Frontend

### Stack Frontend
- **CSS**: Tailwind CSS via CDN (sin build step)
- **Iconos**: FontAwesome 6.4 via CDN
- **JavaScript**: Vanilla JS en templates
- Sin framework SPA; es server-side rendering con AJAX puntual

### Templates Clave
- `facial_recognition.html`: Kiosko principal. Accede a camara del navegador via `getUserMedia()`, captura frame en `<canvas>`, convierte a Blob y hace POST a `/api/registros/verificar_rostro/` para identificar al empleado, luego muestra botones de accion disponibles segun el estado del registro del dia.
- `facial_recognition_comida.html`: Variante del kiosko con flujo de comida diferenciado.
- `register_face.html`: Camara para capturar y guardar rostro de un empleado. POST a `empleados/{id}/registrar-rostro-session/`.
- `dashboard.html`: Metricas personalizadas segun si el usuario es staff o empleado regular.
- `horarios/asignacion_horarios.html`: Vista de calendario mensual para asignar TipoHorario a empleados via drag-and-drop o click. Consume la API `/api/horarios/asignaciones/asignar/` y `/api/horarios/asignaciones/bulk/`.

---

## 13. Variables de Entorno

| Variable | Requerida en Produccion | Descripcion |
|---|---|---|
| `SECRET_KEY` | SI | Django secret key |
| `DEBUG` | SI (False) | Modo debug |
| `ALLOWED_HOSTS` | SI | Hosts permitidos, separados por coma |
| `DATABASE_URL` | SI | URL completa de PostgreSQL |
| `SENDGRID_API_KEY` | SI | Para envio de reportes por email |
| `DEFAULT_FROM_EMAIL` | NO | Email remitente |
| `JWT_ACCESS_TOKEN_LIFETIME` | NO | Minutos, default 60 |
| `JWT_REFRESH_TOKEN_LIFETIME` | NO | Minutos, default 1440 |
| `USE_SPACES` | NO (False) | Habilita DigitalOcean Spaces |
| `DO_SPACES_ACCESS_KEY` | Si USE_SPACES | |
| `DO_SPACES_SECRET_KEY` | Si USE_SPACES | |
| `DO_SPACES_BUCKET_NAME` | Si USE_SPACES | |
| `DO_SPACES_ENDPOINT_URL` | Si USE_SPACES | ej: https://nyc3.digitaloceanspaces.com |
| `DO_SPACES_REGION` | NO | Default: nyc3 |
| `DO_SPACES_CDN_ENDPOINT` | NO | Dominio CDN personalizado |
| `DIGITALOCEAN_APP_DOMAIN` | NO | Auto-agregado a ALLOWED_HOSTS |
| `STATIC_ROOT` | NO | Path de staticfiles, default: staticfiles |
| `MEDIA_ROOT` | NO | Path de media, default: media/checador/ |

---

## 14. Despliegue

### DigitalOcean App Platform
- Archivo `app.yaml`: define servicio web con Dockerfile, 1 instancia `basic-xxs`, puerto 8080
- Health check en `/admin/login/`
- PostgreSQL 16 managed (`checador-db`)
- Deploy automatico en push a `main`

### Procfile (Heroku/Render alternativo)
```
web: gunicorn checador.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 120
```

### Dockerfile
El proyecto incluye Dockerfile para contenerizacion. El `build.sh` probablemente maneja `collectstatic` y `migrate`.

### Archivos especiales para dlib
- `Aptfile`: paquetes del sistema operativo requeridos por dlib (cmake, build-essential, etc.)
- `.buildpacks`: configuracion de buildpacks para Heroku
- `DLIB_FIX.md`: documentacion de problemas con la compilacion de dlib

---

## 15. Patrones Arquitectonicos

### Separacion de Responsabilidades
- **Servicios puros**: `FacialRecognitionService` (sin estado, metodos estaticos) y `horarios/services.py` (funcion pura de resolucion)
- **ViewSets con accion especifica**: serializers diferenciados por accion (`get_serializer_class`)
- **Logica de negocio en modelos**: `calcular_horas_trabajadas()`, `verificar_retardo()`, `calcular_incidencias()`, metodos de transicion de estado en Permiso y Visita

### Doble Canal de Acceso
Para operaciones sensibles como el registro facial, existe un canal API (JWT) y un canal de sesion Django (para el flujo web). Esto permite que el frontend JavaScript del kiosko y el dashboard Django coexistan.

### Resolucion de Horarios en Cascada
El sistema de tres prioridades (AsignacionHorario > Horario semanal > Predeterminado del empleado) permite flexibilidad total: un administrador puede sobrescribir el horario de cualquier empleado en cualquier dia puntual sin modificar la configuracion base.

### Auditoria por Historial
El modulo de permisos implementa un patron de historial explicito (`HistorialPermiso`) que registra cada transicion de estado. Esto proporciona trazabilidad completa sin necesidad de librerias externas como `django-simple-history`.

---

## 16. Gestion de la Zona Horaria

Una constante en todo el proyecto es el manejo explícito de la zona horaria Mexico:

```python
MEXICO_TZ = ZoneInfo('America/Mexico_City')

# En modelos: default calculado en MX time
def fecha_mexico():
    return timezone.now().astimezone(MEXICO_TZ).date()

# En vistas: conversion explicita
ahora_mexico = timezone.now().astimezone(MEXICO_TZ)
hoy = ahora_mexico.date()
hora_actual = ahora_mexico.time()
```

Django guarda todos los timestamps en UTC en la DB (`USE_TZ=True`). La conversion a hora de Mexico se hace en la capa de aplicacion antes de comparar con horarios de entrada/salida.

---

## 17. Areas de Mejora / Deuda Tecnica

### Rendimiento

1. **Scan lineal de empleados en reconocimiento facial**: `recognize_employee()` itera sobre todos los empleados en Python. Con +100 empleados puede volverse lento (cada comparacion es una operacion de algebra lineal). Alternativas:
   - Usar FAISS para busqueda aproximada de vecinos mas cercanos
   - Usar la extension `pgvector` en PostgreSQL para almacenar embeddings como vectores y hacer busqueda por similitud coseno directamente en DB
   - Cachear los encodings en Redis al iniciar la aplicacion

2. **Calculo de estadisticas en Python**: el dashboard y los reportes iteran en Python sobre querysets completos (`sum([r.horas_trabajadas for r in registros])`). Mejor usar `aggregate(Sum('horas_trabajadas'))` del ORM.

3. **Señales globales en storage_backends.py**: `@receiver(post_delete)` sin `sender=` especifico se ejecuta para cada eliminacion en cualquier modelo. Mejor filtrar por modelos especificos con `sender=Empleado`.

### Seguridad

4. **Endpoints AllowAny en registros**: aunque es un requisito del kiosko, seria recomendable al menos implementar un rate limiting (ej: `django-ratelimit`) para prevenir abuso.

5. **Pickle para encodings faciales**: usar `pickle.loads()` en datos almacenados en DB es un vector de ataque si la DB fuera comprometida (deserializacion de objetos arbitrarios). Alternativa mas segura: almacenar el array como JSON de lista de floats.

6. **Secret key hardcodeada por defecto**: el valor default de `SECRET_KEY` en settings.py es una clave insegura de 50 caracteres. Si `DEBUG=True` y no se configura la variable de entorno en un servidor, la aplicacion correria con clave conocida.

### Escalabilidad

7. **Scheduler en proceso web**: `APScheduler` con `BackgroundScheduler` corre en un hilo del mismo proceso de gunicorn. Si hay multiples workers, cada worker intentara ejecutar los jobs. Aunque `DjangoJobStore` con `max_instances=1` mitiga esto, la solucion apropiada para produccion seria Celery + Celery Beat.

8. **Falta de indices en RegistroAsistencia**: el modelo `RegistroAsistencia` tiene `unique_together = ['empleado', 'fecha']` (que crea un indice), pero no hay indices adicionales en campos frecuentemente filtrados como `fecha` individual (para el reporte de todos los empleados de un dia) o `retardo`.

### Calidad de Codigo

9. **Campo departamento duplicado**: `Empleado` tiene tanto `departamento` (CharField legacy) como `departamento_obj` (FK a Departamento estructural). Existe riesgo de inconsistencia entre ambos. El campo legacy deberia depreciarse o mantenerse sincronizado via signal.

10. **Validacion de imagen en kiosko**: la validacion de calidad (`validate_image_quality`) solo ocurre durante el **registro** del rostro, no durante la **verificacion**. En teoria una imagen de baja calidad podria pasar sin advertencia durante la marcacion de asistencia.

11. **Falta de paginacion en ciertas vistas web**: `registros_lista_view` carga todos los registros del rango en memoria sin paginar. Para periodos largos esto puede ser problematico.

---

## 18. Comandos Utiles de Gestion

```bash
# Activar entorno virtual
source .venvChecadorLoginco/bin/activate

# Servidor de desarrollo
python manage.py runserver

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Detectar incidencias del dia anterior
python manage.py detectar_incidencias

# Detectar incidencias de una fecha especifica
python manage.py detectar_incidencias --fecha 2026-01-15

# Enviar reporte manualmente
python manage.py enviar_reporte

# Cargar empleados desde archivo
python manage.py cargar_empleados

# Crear tipos de permiso desde fixtures
python manage.py loaddata permisos/fixtures/tipos_permiso.json

# Archivos estaticos para produccion
python manage.py collectstatic
```

---

## 19. Informacion de Produccion

- **URL en produccion**: `https://checador-loginco-app-zd3ie.ondigitalocean.app`
- **Plataforma**: DigitalOcean App Platform
- **Base de datos**: PostgreSQL 16 managed (cluster `checador-cluster`)
- **Instancia**: `basic-xxs` (1 instancia)
- **Workers Gunicorn**: 2, timeout 120s
- **Health Check**: `/admin/login/`
- **Deploy**: automatico en push a rama `main`
- **Storage**: DigitalOcean Spaces (cuando `USE_SPACES=True`)
- **Email**: SendGrid SMTP
