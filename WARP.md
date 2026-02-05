# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview
Django 6.0 attendance control system with facial recognition. Uses PostgreSQL, OpenCV, face_recognition, JWT authentication, and Tailwind CSS.

## Development Setup

### Environment
- Python 3.10+
- Virtual environment: `.venvChecadorLoginco`
- Activate: `source .venvChecadorLoginco/bin/activate`

### First Time Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Configuration
- Copy `.env.example` to `.env` and configure
- Default: SQLite (for development)
- Production: Uncomment PostgreSQL config in `checador/settings.py` (lines 106-111)

## Common Commands

### Development Server
```bash
python manage.py runserver
# Server runs on http://localhost:8000
# Admin panel: http://localhost:8000/admin
```

### Database Operations
```bash
# Create migrations for all apps
python manage.py makemigrations

# Create migrations for specific app
python manage.py makemigrations <app_name>

# Apply migrations
python manage.py migrate

# Show current migrations status
python manage.py showmigrations
```

### Testing
```bash
# Run all tests
python manage.py test

# Test specific app
python manage.py test <app_name>

# Run with verbosity
python manage.py test --verbosity=2
```

### Static Files
```bash
# Collect static files for production
python manage.py collectstatic --noinput
```

### Django Shell
```bash
# Interactive shell with models loaded
python manage.py shell
```

### Scheduler de Reportes
```bash
# Ver estado de jobs programados
python manage.py scheduler status

# Iniciar scheduler manualmente
python manage.py scheduler start

# Ver historial de ejecuciones
python manage.py scheduler list
python manage.py scheduler list --limit 20

# Enviar reporte manual (comando existente)
python manage.py enviar_reporte diario
python manage.py enviar_reporte semanal
python manage.py enviar_reporte quincenal
```

## Architecture

### Core Apps
1. **authentication/** - JWT-based authentication system
   - Custom login/logout/register views
   - Uses `djangorestframework-simplejwt` with token blacklisting
   - Access token: 60min, Refresh token: 1440min (configurable via .env)

2. **empleados/** - Employee management
   - Model: `Empleado` with OneToOne to Django User
   - Key fields: `codigo_empleado`, `foto_rostro`, `embedding_rostro` (BinaryField)
   - Methods: `set_face_encoding()`, `get_face_encoding()` - pickle serialization of numpy arrays

3. **horarios/** - Schedule management
   - Model: `Horario` with FK to Empleado
   - Supports weekly schedules (Monday=1 to Sunday=7)
   - Includes tolerance for late arrivals (default 10 minutes)

4. **registros/** - Attendance records with facial recognition
   - Model: `RegistroAsistencia` - tracks entrada/salida with automatic calculation
   - Service: `registros/services/facial_recognition.py` - encapsulates face_recognition logic
   - Auto-calculates: `horas_trabajadas`, `retardo` based on horario

### Facial Recognition Service
Located in `registros/services/facial_recognition.py`:
- **FacialRecognitionService** - main service class
- Key parameters:
  - `FACE_TOLERANCE = 0.6` - recognition strictness
  - `MIN_FACE_SIZE = (50, 50)` - minimum face dimensions
  - `MAX_FACES_ALLOWED = 1` - single face per registration
- Key methods:
  - `load_image_from_file()` - handles Django UploadedFile or path
  - `extract_face_encoding()` - validates and extracts face encoding
  - `recognize_employee()` - matches face against all active employees
  - `register_employee_face()` - registers new face encoding

### Models Architecture
- **Empleado.embedding_rostro**: BinaryField storing pickled numpy face encodings
- **RegistroAsistencia**: Unique constraint on (empleado, fecha), auto-calculates hours and tardiness
- **Horario**: Unique constraint on (empleado, dia_semana)

### Authentication Flow
- All API endpoints require JWT auth except:
  - `/api/auth/login/`, `/api/auth/register/`
  - `/api/registros/marcar_entrada/`, `/api/registros/marcar_salida/` (facial recognition endpoints)
- Token refresh rotation enabled with blacklisting

## API Endpoints

### Authentication (`/api/auth/`)
- `POST /login/` - Get JWT tokens
- `POST /register/` - Register new user
- `POST /logout/` - Blacklist refresh token
- `POST /refresh/` - Refresh access token
- `GET /profile/` - Get current user profile
- `PUT /change-password/` - Change password

### Empleados (`/api/empleados/`)
- Standard CRUD: GET, POST, GET/{id}, PUT/{id}, DELETE/{id}
- `POST /{id}/registrar-rostro/` - Register facial encoding (requires `foto_rostro` file)

### Horarios (`/api/horarios/`)
- Standard CRUD operations
- `POST /bulk-create/` - Create multiple schedules at once

### Registros (`/api/registros/`)
- Standard CRUD operations
- `POST /marcar_entrada/` - Mark arrival with facial recognition (no auth required)
- `POST /marcar_salida/` - Mark departure with facial recognition (no auth required)

## Important Patterns

### Adding Face Recognition to Employee
1. Upload photo via `/api/empleados/{id}/registrar-rostro/`
2. Service validates image quality (brightness, blur, face count)
3. Face encoding extracted and stored in `empleado.embedding_rostro` as pickled bytes
4. Original photo saved to `media/rostros/`

### Marking Attendance
1. Client sends photo to `/api/registros/marcar_entrada/`
2. Service extracts face encoding from photo
3. Compares against all active employees with `embedding_rostro`
4. Returns best match with confidence score
5. Creates/updates RegistroAsistencia record
6. Auto-checks tardiness based on horario

### Model Save Hooks
- `RegistroAsistencia.save()` - auto-calculates `horas_trabajadas` and `retardo`
- Always set both `hora_entrada` and `hora_salida` before saving for accurate calculations

## Configuration Notes

### Database Switching
To switch from SQLite to PostgreSQL:
1. Update `.env` with PostgreSQL credentials
2. In `checador/settings.py`, comment lines 104-105, uncomment lines 106-111
3. Create PostgreSQL database: `CREATE DATABASE checador_db;`
4. Run migrations: `python manage.py migrate`

### Timezone
- Set to `America/Mexico_City` in settings
- `USE_TZ = True` - all datetimes stored as UTC

### CORS
- Configured for development: `localhost:3000`, `localhost:8000`
- Modify `CORS_ALLOWED_ORIGINS` in settings.py for production

### Media Files
- `media/rostros/` - employee facial photos
- `media/asistencias/` - attendance record photos
- Served automatically when `DEBUG=True`

## Scheduler Automático de Reportes

### Configuración
- **Sistema**: Django APScheduler (reemplaza cron)
- **Archivo principal**: `reportes/scheduler.py`
- **Inicio automático**: Se inicia al ejecutar `runserver` o `gunicorn` via `reportes/apps.py`
- **Base de datos**: Usa tablas `django_apscheduler_djangojob` y `django_apscheduler_djangojobexecution`

### Horarios Configurados
- **Reporte diario**: Lunes a Sábado, 11:50am
- **Reporte semanal**: Viernes, 11:50am
- **Reporte quincenal**: Días 14 y 29 de cada mes, 11:50am
- **Limpieza de logs**: Diario, 00:00am (elimina ejecuciones >7 días)

### Ventajas sobre Cron
- Integración nativa con Django (acceso al ORM, settings, etc.)
- Logs automáticos en base de datos
- Gestión visual desde el admin de Django
- Portabilidad (funciona en Windows, Docker, etc.)
- No requiere configuración del servidor
- Testing más fácil en desarrollo

### Ver Documentación Completa
- `SCHEDULER_MIGRATION.md` - Guía completa de migración y uso
- Admin panel: Django Apscheduler → Django jobs / Django job executions

## SendGrid Configuration

### Email Settings
- **Backend**: SMTP via SendGrid
- **Configuration**: Lines 259-266 in `checador/settings.py`
- **Required env vars**: `SENDGRID_API_KEY`, `DEFAULT_FROM_EMAIL`

### Testing Email
```bash
# Test SendGrid configuration
python test_sendgrid.py your_email@example.com
```

### Common Issues
- **API Key not configured**: Add `SENDGRID_API_KEY` to `.env` file
- **Sender not verified**: Verify email in SendGrid → Settings → Sender Authentication
- **Free plan limit**: 100 emails/day

### Usage in Code
- Report emails sent via `reportes/services/generador_email.py`
- Uses Django's `send_mail()` and `EmailMultiAlternatives`
- See `SENDGRID_SETUP.md` for detailed setup instructions

## Troubleshooting

### face_recognition_models Warning
- Warning about missing models is normal on startup
- System functions correctly despite warning

### Face Not Recognized
- Check image quality: lighting, focus, face size
- Adjust `FACE_TOLERANCE` in `facial_recognition.py` (lower = stricter)
- Verify employee has `embedding_rostro` set and is active

### Migrations Issues
- Reset: Delete `db.sqlite3` and all `*/migrations/*.py` (except `__init__.py`)
- Fresh start: `python manage.py makemigrations` then `python manage.py migrate`

## Development Notes

### When Creating New Models
1. Add to appropriate app's `models.py`
2. Register in app's `admin.py` for admin panel access
3. Create serializer in `serializers.py` if exposing via API
4. Add URL patterns in app's `urls.py`
5. Run `python manage.py makemigrations <app_name>`
6. Run `python manage.py migrate`

### When Modifying Face Recognition
- Service is in `registros/services/facial_recognition.py`
- Adjust parameters at class level: `FACE_TOLERANCE`, `MIN_FACE_SIZE`, `MAX_FACES_ALLOWED`
- Uses `face_recognition` library (dlib-based), OpenCV for preprocessing
- Encodings are 128-dimensional vectors stored as pickled numpy arrays

### REST Framework Defaults
- Pagination: 20 items per page
- Authentication: JWT required for all endpoints (unless explicitly set to `AllowAny`)
- Filters: SearchFilter and OrderingFilter available
