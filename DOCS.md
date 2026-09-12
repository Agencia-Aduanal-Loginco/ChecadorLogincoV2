# Sistema de Control de Asistencias con Reconocimiento Facial

Sistema completo de control de asistencias desarrollado con Django 6.0, PostgreSQL, OpenCV, face_recognition y Tailwind CSS.

## Características

- ✅ **Autenticación JWT** - Sistema de autenticación seguro con tokens
- 👤 **Reconocimiento Facial** - Registro de asistencias mediante reconocimiento facial
- 📊 **Dashboard Administrativo** - Panel de control con estadísticas
- 📝 **Gestión de Empleados** - CRUD completo de empleados
- ⏰ **Gestión de Horarios** - Configuración de horarios por empleado
- 📋 **Registros de Asistencia** - Historial completo con cálculo automático de horas
- 🎨 **Diseño Responsive** - Interfaz moderna con Tailwind CSS
- 🔒 **Seguridad** - Validaciones y permisos por rol
- 📧 **Reportes Automáticos** - Envío programado vía SendGrid con Django APScheduler
- 🐳 **Docker Ready** - Configuración lista para despliegue en Digital Ocean

## Tecnologías Utilizadas

- **Backend**: Django 6.0
- **Base de Datos**: PostgreSQL (producción) / SQLite (desarrollo)
- **Reconocimiento Facial**: OpenCV, face_recognition, dlib
- **API**: Django REST Framework
- **Autenticación**: Simple JWT con blacklisting
- **Frontend**: Tailwind CSS
- **Reportes**: ReportLab, OpenPyXL
- **Email**: SendGrid (SMTP)
- **Scheduler**: Django APScheduler
- **Storage**: Local / DigitalOcean Spaces (S3-compatible)

---

# Inicio Rápido

## Estado del Proyecto

El sistema está **completamente configurado** y listo para usar:

- ✅ Modelos de base de datos creados y migrados
- ✅ Sistema de reconocimiento facial implementado
- ✅ APIs REST completas con JWT
- ✅ Panel de administración configurado
- ✅ Base de datos SQLite creada (desarrollo)
- ✅ Scheduler de reportes integrado

## Requisitos Previos

- Python 3.10+
- PostgreSQL 13+ (producción)
- pip
- virtualenv (recomendado)

## Iniciar el Servidor

```bash
cd /home/tony/Developer/ChecadorLogincoV2
source .venvChecadorLoginco/bin/activate
python manage.py runserver
```

El servidor estará disponible en: **http://localhost:8000**

## Credenciales de Acceso

### Panel de Administración
- URL: http://localhost:8000/admin/
- **Usuario:** admin
- **Contraseña:** admin123

## Primeros Pasos

### 1. Acceder al Admin
1. Ir a http://localhost:8000/admin/
2. Iniciar sesión con las credenciales
3. Verás el panel con: Empleados, Horarios, Registros de Asistencia

### 2. Obtener Token JWT
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 3. Crear un Empleado
En el admin, ir a "Empleados" → "Agregar empleado", completar información y guardar.

### 4. Registrar Rostro Facial
```bash
curl -X POST http://localhost:8000/api/empleados/1/registrar-rostro/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "foto_rostro=@path/to/photo.jpg"
```

### 5. Configurar Horarios
```bash
curl -X POST http://localhost:8000/api/horarios/bulk-create/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "empleado": 1,
    "horarios": [
      {"dia_semana": 1, "hora_entrada": "09:00", "hora_salida": "18:00"},
      {"dia_semana": 2, "hora_entrada": "09:00", "hora_salida": "18:00"}
    ]
  }'
```

### 6. Marcar Asistencia
```bash
curl -X POST http://localhost:8000/api/registros/marcar_entrada/ \
  -F "foto=@/path/to/selfie.jpg"
```

---

# Instalación Completa

### 1. Clonar el repositorio
```bash
cd /home/tony/Developer/ChecadorLogincoV2
```

### 2. Crear y activar entorno virtual
```bash
python -m venv .venvChecadorLoginco
source .venvChecadorLoginco/bin/activate  # Linux/Mac
# o
.venvChecadorLoginco\Scripts\activate     # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Editar el archivo `.env` con tus credenciales:
```env
# Django Settings
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=checador_db
DB_USER=postgres
DB_PASSWORD=tu-password-postgres
DB_HOST=localhost
DB_PORT=5432

# JWT Settings
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440

# SendGrid Email
SENDGRID_API_KEY=SG.tu_api_key_aqui
DEFAULT_FROM_EMAIL=Sistema de Checador <notificaciones@loginco.com.mx>

# Storage (opcional, para DigitalOcean Spaces)
USE_SPACES=False
# DO_SPACES_KEY=...
# DO_SPACES_SECRET=...
```

### 5. Configurar PostgreSQL (producción)
```sql
CREATE DATABASE checador_db;
CREATE USER postgres WITH PASSWORD 'postgres';
ALTER ROLE postgres SET client_encoding TO 'utf8';
ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';
ALTER ROLE postgres SET timezone TO 'America/Mexico_City';
GRANT ALL PRIVILEGES ON DATABASE checador_db TO postgres;
```

> **Nota:** Para desarrollo, el sistema usa SQLite por defecto. Para PostgreSQL, descomentar las líneas en `checador/settings.py` (líneas 106-111) y comentar las de SQLite (líneas 104-105).

### 6. Ejecutar migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear superusuario
```bash
python manage.py createsuperuser
```

### 8. Iniciar el servidor
```bash
python manage.py runserver
```

---

# Arquitectura

## Estructura del Proyecto

```
ChecadorLogincoV2/
├── checador/               # Configuración principal del proyecto
│   ├── settings.py        # Configuraciones
│   ├── urls.py            # URLs principales
│   ├── views.py           # Vistas web (dashboard, login, facial check-in)
│   └── wsgi.py
├── authentication/         # App de autenticación JWT
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── empleados/             # App de gestión de empleados
│   ├── models.py          # Modelo Empleado
│   ├── serializers.py
│   ├── views.py
│   ├── admin.py
│   └── urls.py
├── horarios/              # App de gestión de horarios
│   ├── models.py          # Modelo Horario
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── registros/             # App de registros de asistencia
│   ├── models.py          # Modelo RegistroAsistencia
│   ├── serializers.py
│   ├── views.py
│   ├── services/
│   │   └── facial_recognition.py
│   └── urls.py
├── reportes/              # App de reportes automáticos
│   ├── scheduler.py       # Django APScheduler jobs
│   ├── services/
│   │   └── generador_email.py
│   ├── management/commands/
│   │   └── scheduler.py   # Comando de gestión
│   └── apps.py            # Auto-inicio del scheduler
├── templates/             # Templates HTML
├── static/                # Archivos estáticos
├── media/                 # Archivos subidos
│   ├── rostros/          # Fotos de empleados
│   └── asistencias/      # Fotos de registros
├── docs/                  # Documentación adicional
├── Dockerfile             # Configuración Docker
├── app.yaml               # Config Digital Ocean App Platform
├── requirements.txt
├── .env
└── manage.py
```

## Apps de Django

### 1. checador/ - Configuración principal
- Configuración del proyecto (settings.py, urls.py)
- Vistas web: `/login/`, `/register/`, `/logout/`, `/dashboard/`, `/empleados/`, `/registros/`
- Página de check-in facial: `/` y `/facial/`

### 2. authentication/ - Autenticación JWT
- JWT via `djangorestframework-simplejwt` con blacklisting
- Access token: 60min, Refresh token: 1440min (configurable via .env)
- Custom login/logout/register views

### 3. empleados/ - Gestión de empleados
- Modelo `Empleado` con OneToOne a Django User
- Campos clave: `codigo_empleado`, `foto_rostro`, `embedding_rostro` (BinaryField)
- Métodos: `set_face_encoding()`, `get_face_encoding()` - serialización pickle de arrays numpy

### 4. horarios/ - Gestión de horarios
- Modelo `Horario` con FK a Empleado
- Horarios semanales (Lunes=1 a Domingo=7)
- Tolerancia para retardos (default 10 minutos)

### 5. registros/ - Registros de asistencia
- Modelo `RegistroAsistencia` - tracks entrada/salida con cálculo automático
- Servicio: `registros/services/facial_recognition.py`
- Auto-calcula: `horas_trabajadas`, `retardo` basado en horario

### 6. reportes/ - Reportes automáticos
- Django APScheduler para envío programado
- Generador de emails vía SendGrid
- Logs automáticos en base de datos

## Modelos

### Empleado
- **embedding_rostro**: BinaryField que almacena encodings faciales pickled (numpy arrays de 128 dimensiones)
- **foto_rostro**: ImageField almacenada en `media/rostros/`
- **eliminar_rostro()**: Método para eliminar registro facial completo

### RegistroAsistencia
- Constraint único en (empleado, fecha)
- Auto-calcula horas trabajadas y retardo al guardar
- Almacena fotos de check-in en `media/asistencias/`
- Incluye coordenadas GPS y nivel de confianza del reconocimiento facial

### Horario
- Constraint único en (empleado, dia_semana)
- Campos: día de semana, hora entrada, hora salida, minutos de tolerancia

## Flujo de Autenticación

- Todos los endpoints API requieren JWT auth excepto:
  - `/api/auth/login/`, `/api/auth/register/`
  - `/api/registros/marcar_entrada/`, `/api/registros/marcar_salida/` (endpoints de reconocimiento facial)
- Token refresh rotation habilitado con blacklisting

## Vistas Web (Session-based)

- `/login/`, `/register/`, `/logout/` - Auth basada en sesiones
- `/dashboard/` - Dashboard administrativo
- `/empleados/`, `/registros/` - Vistas de staff
- `/` y `/facial/` - Página de check-in facial

## Storage

Backends configurables:
- **Local**: WhiteNoise para estáticos, filesystem local para media
- **DigitalOcean Spaces**: `USE_SPACES=True`, S3-compatible via django-storages

## Configuración

### Timezone
- `TIME_ZONE = 'America/Mexico_City'`
- `USE_TZ = True` - datetimes almacenados como UTC
- Idioma: `es-mx`

### CORS
- Desarrollo: `localhost:3000`, `localhost:8000`
- Producción: Modificar `CORS_ALLOWED_ORIGINS` en settings.py

### REST Framework
- Paginación: 20 items por página
- Autenticación: JWT requerida para todos los endpoints (salvo `AllowAny`)
- Filtros: SearchFilter y OrderingFilter disponibles

---

# API Endpoints

## Autenticación (`/api/auth/`)
- `POST /login/` - Obtener tokens JWT
- `POST /register/` - Registrar nuevo usuario
- `POST /logout/` - Blacklist refresh token
- `POST /refresh/` - Refrescar access token
- `GET /profile/` - Obtener perfil del usuario
- `PUT /change-password/` - Cambiar contraseña

## Empleados (`/api/empleados/`)
- `GET /` - Listar empleados
- `POST /` - Crear empleado
- `GET /{id}/` - Detalle de empleado
- `PUT /{id}/` - Actualizar empleado
- `DELETE /{id}/` - Eliminar empleado
- `POST /{id}/registrar-rostro/` - Registrar rostro facial (requiere JWT + archivo `foto_rostro`)
- `POST /{id}/eliminar-rostro/` - Eliminar registro facial (requiere JWT)
- `POST /{id}/eliminar-rostro-session/` - Eliminar rostro via sesión (solo staff)

## Horarios (`/api/horarios/`)
- `GET /` - Listar horarios
- `POST /` - Crear horario
- `GET /{id}/` - Detalle de horario
- `PUT /{id}/` - Actualizar horario
- `DELETE /{id}/` - Eliminar horario
- `POST /bulk-create/` - Crear múltiples horarios

## Registros de Asistencia (`/api/registros/`)
- `GET /` - Listar registros
- `POST /` - Crear registro manual
- `GET /{id}/` - Detalle de registro
- `PUT /{id}/` - Actualizar registro
- `POST /marcar_entrada/` - Marcar entrada con reconocimiento facial (sin auth)
- `POST /marcar_salida/` - Marcar salida con reconocimiento facial (sin auth)

---

# Reconocimiento Facial

## Servicio Principal

Ubicado en `registros/services/facial_recognition.py`:

### Clase: FacialRecognitionService

**Parámetros configurables:**
- `FACE_TOLERANCE = 0.6` - Tolerancia para comparación (menor = más estricto)
- `MIN_FACE_SIZE = (50, 50)` - Tamaño mínimo del rostro en píxeles
- `MAX_FACES_ALLOWED = 1` - Máximo de rostros en imagen de registro

**Métodos principales:**
- `load_image_from_file()` - Carga imágenes desde UploadedFile o path
- `extract_face_encoding()` - Valida calidad (brillo, blur, tamaño) y extrae encoding
- `recognize_employee()` - Compara contra todos los empleados activos con `embedding_rostro`
- `register_employee_face()` - Registra nuevo encoding facial

### Flujo de Registro de Rostro
1. Upload de foto via `/api/empleados/{id}/registrar-rostro/`
2. Servicio valida calidad de imagen (brillo, blur, conteo de rostros)
3. Encoding facial extraído y almacenado en `empleado.embedding_rostro` como bytes pickled
4. Foto original guardada en `media/rostros/`

### Flujo de Marcado de Asistencia
1. Cliente envía foto a `/api/registros/marcar_entrada/`
2. Servicio extrae encoding facial de la foto
3. Compara contra todos los empleados activos
4. Retorna mejor match con porcentaje de confianza
5. Crea/actualiza registro de RegistroAsistencia
6. Auto-verifica retardo basado en horario

## Eliminación de Rostros

### Casos de uso
- Registro del rostro de otra persona por error
- Foto con mala calidad que causa falsos negativos
- Necesidad de actualizar completamente el registro facial

### Endpoints

**REST API (JWT):**
- `POST /api/empleados/{id}/eliminar-rostro/`

**Session API (cookies):**
- `POST /api/empleados/{id}/eliminar-rostro-session/` (solo staff)

### Flujo desde la interfaz web
1. Admin → Empleados → Seleccionar empleado
2. Click en "Ver/Actualizar" en columna "Gestión de Rostro"
3. Click en icono de basura (🗑️) junto al badge "Rostro Registrado"
4. Confirmar eliminación → Registrar nuevo rostro

### Eliminación masiva desde admin
1. Admin → Empleados → Seleccionar empleados
2. Acciones → "Eliminar rostros faciales de empleados seleccionados"
3. Click en "Ir" → Confirmar

### Notas
- Al eliminar, se borran `embedding_rostro` (encoding) y `foto_rostro` (archivo)
- El archivo físico se elimina del storage (local o S3)
- No hay límite de re-registros
- La eliminación es permanente (sin papelera)

---

# Scheduler Automático de Reportes

## Descripción

Sistema de envío automático de reportes de asistencia usando **Django APScheduler** (reemplaza cron).

### Ventajas sobre Cron
1. Todo dentro de Django - sin configuración del servidor
2. Logs automáticos en base de datos
3. Monitoreo visual desde admin de Django
4. Funciona en cualquier SO (Windows, Linux, macOS, Docker)
5. Fácil de probar en desarrollo
6. Configuración en Python en lugar de sintaxis cron
7. Integración completa con ORM y settings de Django

## Configuración

- **Archivo principal**: `reportes/scheduler.py`
- **Inicio automático**: Se inicia al ejecutar `runserver` o `gunicorn` vía `reportes/apps.py`
- **Base de datos**: Usa tablas `django_apscheduler_djangojob` y `django_apscheduler_djangojobexecution`
- **Dependencia**: `django-apscheduler==0.6.2`

## Horarios Configurados

- **Reporte diario**: Lunes a Sábado, 11:50am
- **Reporte semanal**: Viernes, 11:50am
- **Reporte quincenal**: Días 14 y 29 de cada mes, 11:50am
- **Limpieza de logs**: Diario, 00:00am (elimina ejecuciones >7 días)

## Comandos

### Ver estado de jobs
```bash
python manage.py scheduler status
```

### Ver historial de ejecuciones
```bash
python manage.py scheduler list
python manage.py scheduler list --limit 20
```

### Iniciar scheduler manualmente
```bash
python manage.py scheduler start
```

### Enviar reporte manual
```bash
# --empresa (codigo) es obligatorio para diario/semanal/quincenal, ya que
# cada empresa tiene su propia configuracion y destinatarios
python manage.py enviar_reporte diario --empresa LOGINCO
python manage.py enviar_reporte semanal --empresa LOGINCO
python manage.py enviar_reporte quincenal --empresa LOGINCO
python manage.py enviar_reporte diario --empresa LOGINCO --email test@example.com
```

## Monitoreo

### Desde la consola
```bash
python manage.py scheduler status
python manage.py scheduler list --limit 20
```

### Desde el Admin de Django
1. Acceder a: `http://localhost:8000/admin`
2. **Django Apscheduler → Django jobs**: Jobs programados y próximas ejecuciones
3. **Django Apscheduler → Django job executions**: Historial completo con errores
4. **Reportes → Logs de Reportes**: Registro de envíos (`LogReporte`)

## Producción con Gunicorn

```bash
# Single worker (scheduler incluido)
gunicorn checador.wsgi:application --workers 1

# Múltiples workers (scheduler separado)
gunicorn checador.wsgi:application --workers 4 &
python manage.py scheduler start
```

## Cambiar horarios

Editar `reportes/scheduler.py`, sección `start_scheduler()`:
```python
# Ejemplo: Cambiar reporte diario a 9:00am
scheduler.add_job(
    enviar_reporte_diario,
    trigger=CronTrigger(day_of_week="mon-sat", hour=9, minute=0),
    id="reporte_diario",
    max_instances=1,
    replace_existing=True,
    name="Envio de reporte diario"
)
```
Reiniciar Django después del cambio.

## Probar jobs inmediatamente

```bash
# Opción 1: Comando manual
python manage.py enviar_reporte diario --empresa LOGINCO

# Opción 2: Python shell
python manage.py shell
>>> from reportes.scheduler import enviar_reporte_diario
>>> enviar_reporte_diario()
```

## Migración desde Cron

### Resumen
- **Estado**: ✅ Migración completada (2026-01-30)
- `crontab.txt` está deprecado (mantener como referencia histórica)
- `django-apscheduler==0.6.2` agregado a `requirements.txt`
- `django_apscheduler` agregado a `INSTALLED_APPS`
- Migraciones ejecutadas para tablas del scheduler

### Pasos realizados
1. Agregado `django-apscheduler` como dependencia
2. Creado `reportes/scheduler.py` con todos los jobs
3. Creado comando de gestión `reportes/management/commands/scheduler.py`
4. Modificado `reportes/apps.py` para auto-inicio
5. Deprecado `crontab.txt`

### Aplicar en producción
```bash
git pull origin main
source .venvChecadorLoginco/bin/activate
pip install -r requirements.txt
python manage.py migrate
crontab -r  # Desactivar crontabs antiguos
# Reiniciar servidor Django
```

---

# Configuración de SendGrid (Email)

## Requisitos
1. Cuenta activa en [SendGrid](https://sendgrid.com/)
2. API Key de SendGrid generada
3. Email remitente verificado en SendGrid

## Paso 1: Obtener API Key

1. Ve a **Settings** → **API Keys** en SendGrid
2. Click en **Create API Key**
3. Nombre descriptivo (ej: "Checador Loginco Production")
4. Selecciona **Full Access** o permisos de envío
5. **Copia la API Key inmediatamente** (solo se muestra una vez)
   - Formato: `SG.xxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyy`

## Paso 2: Verificar Email Remitente

### Single Sender Verification (desarrollo)
1. **Settings** → **Sender Authentication** → **Verify a Single Sender**
2. Completar: From Name, From Email, Reply To
3. Click en el link de verificación en tu email

### Domain Authentication (producción)
1. **Settings** → **Sender Authentication** → **Authenticate Your Domain**
2. Agregar registros DNS según instrucciones
3. Esperar verificación (hasta 48 horas)

## Paso 3: Configurar .env

```bash
# SendGrid Email Configuration
SENDGRID_API_KEY=SG.tu_api_key_completa_aqui
DEFAULT_FROM_EMAIL=Sistema de Checador <notificaciones@loginco.com.mx>
```

**Importante**: El email en `DEFAULT_FROM_EMAIL` debe coincidir con el verificado en SendGrid.

## Paso 4: Probar

```bash
source .venvChecadorLoginco/bin/activate
python test_sendgrid.py tu_email@ejemplo.com
```

Resultado esperado:
```
✅ EMAIL_BACKEND: django.core.mail.backends.smtp.EmailBackend
✅ EMAIL_HOST: smtp.sendgrid.net
✅ EMAIL_PORT: 587
✅ EMAIL_HOST_PASSWORD: ***configurada***
✅ Email enviado exitosamente!
```

## Uso en el Código

Los reportes se envían automáticamente desde `reportes/services/generador_email.py`.

Para enviar emails manualmente:
```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    subject='Asunto del email',
    message='Contenido en texto plano',
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['destinatario@ejemplo.com'],
    fail_silently=False,
)
```

## Configuración en settings.py
- **Backend**: SMTP vía SendGrid (líneas 259-266)
- **Env vars requeridas**: `SENDGRID_API_KEY`, `DEFAULT_FROM_EMAIL`
- **Límite plan gratuito**: 100 emails/día

## Producción (DigitalOcean/Render)

Agregar variables de entorno:
```
SENDGRID_API_KEY=tu_api_key_de_produccion
DEFAULT_FROM_EMAIL=Sistema de Checador <notificaciones@loginco.com.mx>
```

Se recomienda Domain Authentication para mejor deliverability.

---

# Despliegue

## Digital Ocean App Platform (Docker)

El proyecto usa **Docker** para despliegue, lo que resuelve problemas de compilación de `dlib`.

### Archivos de Configuración
- `Dockerfile` - Imagen Docker optimizada (Python 3.12 slim)
- `.dockerignore` - Archivos excluidos del build
- `app.yaml` - Configuración de Digital Ocean App Platform
- `Aptfile` - Dependencias del sistema Linux
- `Procfile` - Comando de inicio con Gunicorn
- `runtime.txt` - Versión de Python
- `build.sh` - Script de construcción
- `.buildpacks` - Orden de buildpacks

### Variables de Entorno Requeridas

```bash
# Django
DEBUG=False
SECRET_KEY=tu-secret-key-segura
DJANGO_SETTINGS_MODULE=checador.settings
ALLOWED_HOSTS=tu-app.ondigitalocean.app

# Base de datos PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database

# JWT
ACCESS_TOKEN_LIFETIME_MINUTES=60
REFRESH_TOKEN_LIFETIME_MINUTES=1440

# CORS (opcional)
CORS_ALLOWED_ORIGINS=https://tu-frontend.com

# SendGrid
SENDGRID_API_KEY=tu_api_key
DEFAULT_FROM_EMAIL=Sistema de Checador <notificaciones@loginco.com.mx>
```

### Opción 1: Deploy Automático

1. Push a la rama `main`:
   ```bash
   git add .
   git commit -m "Configure Docker deployment"
   git push origin main
   ```
2. Digital Ocean detectará automáticamente los cambios

### Opción 2: Deploy Manual (interfaz web)

1. Ir a **App Platform** → **Crear Nueva App**
2. Conectar repositorio de GitHub
3. Configurar variables de entorno
4. **Build Command**:
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
   ```
5. **Run Command**:
   ```bash
   gunicorn checador.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 120
   ```
6. Agregar base de datos PostgreSQL
7. Health Check: Path `/admin/login/`, Port `8080`

### Opción 3: doctl CLI

```bash
doctl auth init
doctl apps create --spec app.yaml
doctl apps logs <app-id> --follow
```

### Base de Datos PostgreSQL

Digital Ocean puede provisionar automáticamente:
1. Dashboard → Database → Crear PostgreSQL cluster
2. En tu app → Resources → Añadir base de datos
3. Digital Ocean configurará `DATABASE_URL` automáticamente

Para usar `DATABASE_URL` en settings.py:
```python
import dj_database_url

if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
```

### Dockerfile

El Dockerfile incluido:
- ✅ Python 3.12 slim (menor tamaño)
- ✅ Dependencias del sistema para dlib y OpenCV
- ✅ Compilación correcta de dlib
- ✅ collectstatic automático
- ✅ Migraciones en el inicio

### Verificación Post-Despliegue

```bash
# Verificar app
curl https://tu-app.ondigitalocean.app/admin/login/

# Crear superusuario
python manage.py createsuperuser

# Ver logs
doctl apps logs <app-id> --follow
```

### Seguridad en Producción

- ✅ HTTPS habilitado automáticamente
- ✅ `DEBUG=False`
- ✅ `SECRET_KEY` segura en variables de entorno
- ✅ CORS configurado correctamente
- ✅ CSRF protection habilitado
- ✅ WhiteNoise para archivos estáticos
- ✅ NUNCA hacer commit de `.env` o secretos

### Costos Estimados
- **Basic Plan**: ~$5-12/mes
- **PostgreSQL Database**: ~$7/mes
- **Storage**: Incluido en plan básico

### Comandos Útiles

```bash
doctl apps get <app-id>           # Info de la app
doctl apps spec get <app-id>      # Variables de entorno
doctl apps restart <app-id>       # Reiniciar
doctl apps list-builds <app-id>   # Ver builds
doctl apps list-deployments <app-id>  # Listar deployments
doctl apps rollback <app-id> <deployment-id>  # Rollback
```

## Solución: Error de Compilación de dlib

### Problema
```
Failed to build dlib
ERROR: Failed to build installable wheels for some pyproject.toml based projects (dlib)
```

### Causa
`dlib` necesita compilarse desde código fuente y requiere herramientas de compilación (g++, cmake), bibliotecas matemáticas (BLAS, LAPACK) y dependencias de desarrollo.

### Solución Implementada

**Aptfile** con dependencias del sistema:
```
build-essential, cmake, g++, gfortran, pkg-config
libopenblas-dev, liblapack-dev, libx11-dev, libjpeg-dev, libpng-dev
libgl1-mesa-glx, libglib2.0-0, libsm6, libxext6, libxrender-dev, libgomp1
```

**Orden correcto de instalación** (en `build.sh`):
1. Sistema: apt-get install dependencias
2. Python base: pip, setuptools, wheel
3. numpy < 2.0 (requerido por dlib)
4. dlib == 19.24.2 (compilado desde fuente)
5. face_recognition (usa dlib ya instalado)
6. opencv-python-headless (sin GUI, más ligero)
7. Resto de dependencias

**Notas:**
- dlib necesita mínimo 1GB RAM para compilar
- Compilación toma 3-5 minutos
- Digital Ocean cachea después del primer build exitoso
- Para Docker: todo resuelto en el Dockerfile

---

# Comandos Comunes de Desarrollo

## Servidor
```bash
python manage.py runserver
# http://localhost:8000
# Admin: http://localhost:8000/admin
```

## Base de Datos
```bash
python manage.py makemigrations              # Crear migraciones
python manage.py makemigrations <app_name>   # Migraciones específicas
python manage.py migrate                     # Aplicar migraciones
python manage.py showmigrations              # Estado de migraciones
```

## Testing
```bash
python manage.py test                    # Todos los tests
python manage.py test <app_name>         # Tests de app específica
python manage.py test --verbosity=2      # Con detalle
```

## Otros
```bash
python manage.py createsuperuser              # Crear superusuario
python manage.py collectstatic --noinput      # Archivos estáticos
python manage.py shell                        # Shell interactivo
python test_sendgrid.py email@ejemplo.com     # Test de SendGrid
```

---

# Guía para IA (WARP / Claude Code)

## Patrones Importantes

### Al Crear Nuevos Modelos
1. Agregar a `models.py` del app correspondiente
2. Registrar en `admin.py` para el panel de admin
3. Crear serializer en `serializers.py` si se expone via API
4. Agregar URL patterns en `urls.py` del app
5. Ejecutar `python manage.py makemigrations <app_name>`
6. Ejecutar `python manage.py migrate`

### Al Modificar Reconocimiento Facial
- Servicio en `registros/services/facial_recognition.py`
- Ajustar parámetros a nivel de clase: `FACE_TOLERANCE`, `MIN_FACE_SIZE`, `MAX_FACES_ALLOWED`
- Usa `face_recognition` library (basada en dlib), OpenCV para preprocessing
- Encodings son vectores de 128 dimensiones almacenados como numpy arrays pickled

### Model Save Hooks
- `RegistroAsistencia.save()` auto-calcula `horas_trabajadas` y `retardo`
- Siempre setear `hora_entrada` y `hora_salida` antes de guardar

---

# Troubleshooting

## face_recognition_models Warning
- Warning sobre modelos faltantes es normal al iniciar
- El sistema funciona correctamente a pesar del warning

## Rostro No Reconocido
- Verificar calidad de imagen: iluminación, enfoque, tamaño de rostro
- Ajustar `FACE_TOLERANCE` en `facial_recognition.py` (menor = más estricto)
- Verificar que el empleado tiene `embedding_rostro` seteado y está activo

## Problemas de Migraciones
- Reset: Eliminar `db.sqlite3` y todos los `*/migrations/*.py` (excepto `__init__.py`)
- Fresh start: `python manage.py makemigrations` luego `python manage.py migrate`

## Scheduler no Inicia
- Verificar que `django_apscheduler` esté en `INSTALLED_APPS`
- Ejecutar `python manage.py migrate`
- Revisar logs para errores de importación

## Jobs no se Ejecutan
- Verificar que Django esté corriendo: `python manage.py scheduler status`
- Revisar zona horaria en `settings.py`: `TIME_ZONE = 'America/Mexico_City'`
- Reportes duplicados → usar single worker o scheduler en proceso separado

## Error de SendGrid
- **API Key no configurada**: Agregar `SENDGRID_API_KEY` a `.env`
- **Authentication failed**: Verificar/regenerar API Key
- **Sender address rejected**: Verificar email en SendGrid → Sender Authentication
- **Email no llega**: Revisar SPAM, SendGrid Dashboard → Activity
- **Límite plan gratuito**: 100 emails/día

## Despliegue - Errores Comunes

### Error 502 Bad Gateway
- Verificar que el puerto sea 8080
- Revisar logs: `doctl apps logs <app-id>`

### Static files no se cargan
- Verificar que `whitenoise` esté instalado
- Ejecutar `python manage.py collectstatic`

### Error de CSRF
- Agregar dominio a `ALLOWED_HOSTS`
- Configurar `CSRF_TRUSTED_ORIGINS`

### Error: "dlib failed to build"
- Usar Docker (resuelve automáticamente)
- O verificar Aptfile + build.sh

### Error: "ModuleNotFoundError: MySQLdb"
- Digital Ocean detectó MySQL en vez de PostgreSQL
- Verificar que `DATABASE_URL` empiece con `postgresql://`
- Eliminar cualquier DB MySQL en Resources

### Error: "collectstatic failed"
- Verificar `STATIC_ROOT = BASE_DIR / 'staticfiles'` en settings.py

### Servidor no Inicia
```bash
source .venvChecadorLoginco/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

---

# Seguridad

- Las contraseñas se almacenan con hash
- JWT tokens con expiración configurable
- CORS configurado para desarrollo/producción
- Validaciones en todas las entradas
- Permisos por rol (admin, staff, empleado)
- HTTPS en producción (automático en Digital Ocean)
- `.env` en `.gitignore` - nunca hacer commit de secretos

---

# Contribución

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Crea un Pull Request

---

# Licencia

Este proyecto es privado y propietario.

## Soporte

Para soporte, contactar al equipo de desarrollo.

## Referencias

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [face_recognition](https://github.com/ageitgey/face_recognition)
- [dlib C++ Library](http://dlib.net/)
- [Django APScheduler](https://github.com/jcass77/django-apscheduler)
- [SendGrid Documentation](https://docs.sendgrid.com/)
- [Digital Ocean App Platform](https://docs.digitalocean.com/products/app-platform/)
- [Digital Ocean Docker en App Platform](https://docs.digitalocean.com/products/app-platform/reference/dockerfile/)
