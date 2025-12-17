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

## Requisitos Previos

- Python 3.10+
- PostgreSQL 13+
- pip
- virtualenv (recomendado)

## Instalación

### 1. Clonar el repositorio (o usar el directorio actual)

```bash
cd /home/xoyoc/Developer/ChecadorLogincoV2
```

### 2. Crear y activar entorno virtual

```bash
python -m venv .venvChecadorLoginco
source .venvChecadorLoginco/bin/activate  # En Linux/Mac
# o
.venvChecadorLoginco\Scripts\activate  # En Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar PostgreSQL

Crear la base de datos en PostgreSQL:

```sql
CREATE DATABASE checador_db;
CREATE USER postgres WITH PASSWORD 'postgres';
ALTER ROLE postgres SET client_encoding TO 'utf8';
ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';
ALTER ROLE postgres SET timezone TO 'America/Mexico_City';
GRANT ALL PRIVILEGES ON DATABASE checador_db TO postgres;
```

### 5. Configurar variables de entorno

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
```

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

El sistema estará disponible en: `http://localhost:8000`

## Estructura del Proyecto

```
ChecadorLogincoV2/
├── checador/               # Configuración principal del proyecto
│   ├── settings.py        # Configuraciones
│   ├── urls.py            # URLs principales
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
│   ├── services/          # Servicios de reconocimiento facial
│   │   └── facial_recognition.py
│   └── urls.py
├── templates/             # Templates HTML
│   └── base.html
├── static/                # Archivos estáticos
│   ├── css/
│   ├── js/
│   └── img/
├── media/                 # Archivos subidos
│   ├── rostros/          # Fotos de empleados
│   └── asistencias/      # Fotos de registros
├── requirements.txt       # Dependencias
├── .env                   # Variables de entorno
└── manage.py
```

## API Endpoints

### Autenticación
- `POST /api/auth/login/` - Obtener token JWT
- `POST /api/auth/refresh/` - Refrescar token
- `POST /api/auth/register/` - Registrar nuevo usuario
- `POST /api/auth/logout/` - Cerrar sesión
- `GET /api/auth/profile/` - Obtener perfil del usuario
- `PUT /api/auth/change-password/` - Cambiar contraseña

### Empleados
- `GET /api/empleados/` - Listar empleados
- `POST /api/empleados/` - Crear empleado
- `GET /api/empleados/{id}/` - Detalle de empleado
- `PUT /api/empleados/{id}/` - Actualizar empleado
- `DELETE /api/empleados/{id}/` - Eliminar empleado
- `POST /api/empleados/{id}/registrar-rostro/` - Registrar rostro facial

### Horarios
- `GET /api/horarios/` - Listar horarios
- `POST /api/horarios/` - Crear horario
- `GET /api/horarios/{id}/` - Detalle de horario
- `PUT /api/horarios/{id}/` - Actualizar horario
- `DELETE /api/horarios/{id}/` - Eliminar horario
- `POST /api/horarios/bulk-create/` - Crear múltiples horarios

### Registros de Asistencia
- `GET /api/registros/` - Listar registros
- `POST /api/registros/` - Crear registro manual
- `GET /api/registros/{id}/` - Detalle de registro
- `PUT /api/registros/{id}/` - Actualizar registro
- `POST /api/registros/marcar_entrada/` - Marcar entrada con reconocimiento facial
- `POST /api/registros/marcar_salida/` - Marcar salida con reconocimiento facial

## Uso del Sistema

### 1. Registrar Empleado

1. Acceder al panel de administración: `http://localhost:8000/admin`
2. Ir a "Empleados" y crear uno nuevo
3. Completar los datos del empleado

### 2. Registrar Rostro Facial

Usar el endpoint API:
```bash
curl -X POST http://localhost:8000/api/empleados/1/registrar-rostro/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "foto_rostro=@/path/to/photo.jpg"
```

### 3. Configurar Horarios

Crear horarios para el empleado:
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

### 4. Marcar Asistencia

Marcar entrada con reconocimiento facial:
```bash
curl -X POST http://localhost:8000/api/registros/marcar_entrada/ \
  -F "foto=@/path/to/selfie.jpg"
```

## Configuración del Reconocimiento Facial

El servicio de reconocimiento facial tiene los siguientes parámetros configurables en `registros/services/facial_recognition.py`:

- `FACE_TOLERANCE`: Tolerancia para comparación (default: 0.6)
- `MIN_FACE_SIZE`: Tamaño mínimo del rostro en píxeles (default: 50x50)
- `MAX_FACES_ALLOWED`: Máximo de rostros en imagen de registro (default: 1)

## Seguridad

- Las contraseñas se almacenan con hash
- JWT tokens con expiración configurable
- CORS configurado para desarrollo
- Validaciones en todas las entradas
- Permisos por rol (admin, staff, empleado)

## Testing

```bash
python manage.py test
```

## Deployment

Para producción, asegúrate de:

1. Cambiar `DEBUG=False` en `.env`
2. Configurar `SECRET_KEY` segura
3. Configurar `ALLOWED_HOSTS` apropiadamente
4. Usar servidor de base de datos dedicado
5. Configurar archivos estáticos con `collectstatic`
6. Usar servidor WSGI (gunicorn, uwsgi)
7. Configurar HTTPS

## Tecnologías Utilizadas

- **Backend**: Django 6.0
- **Base de Datos**: PostgreSQL
- **Reconocimiento Facial**: OpenCV, face_recognition, dlib
- **API**: Django REST Framework
- **Autenticación**: Simple JWT
- **Frontend**: Tailwind CSS
- **Reportes**: ReportLab, OpenPyXL

## Contribución

Para contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Crea un Pull Request

## Licencia

Este proyecto es privado y propietario.

## Soporte

Para soporte, contactar al equipo de desarrollo.
