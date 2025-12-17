# Inicio Rápido - Sistema de Asistencias

## ✅ Estado del Proyecto

El sistema está **completamente configurado** y listo para usar:

- ✅ Modelos de base de datos creados y migrados
- ✅ Sistema de reconocimiento facial implementado
- ✅ APIs REST completas con JWT
- ✅ Panel de administración configurado
- ✅ Base de datos SQLite creada
- ✅ Superusuario creado

## 🚀 Iniciar el Servidor

```bash
cd /home/xoyoc/Developer/ChecadorLogincoV2
source .venvChecadorLoginco/bin/activate
python manage.py runserver
```

El servidor estará disponible en: **http://localhost:8000**

## 🔐 Credenciales de Acceso

### Panel de Administración
- URL: http://localhost:8000/admin/
- **Usuario:** admin
- **Contraseña:** admin123

## 📝 Primeros Pasos

### 1. Acceder al Admin
1. Ir a http://localhost:8000/admin/
2. Iniciar sesión con las credenciales arriba
3. Verás el panel con: Empleados, Horarios, Registros de Asistencia

### 2. Crear un Empleado
1. En el admin, ir a "Empleados" → "Agregar empleado"
2. Primero crear un usuario desde "Usuarios" o usar el formulario
3. Completar información del empleado
4. Guardar

### 3. Registrar Rostro Facial
Usar el API endpoint:
```bash
curl -X POST http://localhost:8000/api/empleados/1/registrar-rostro/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "foto_rostro=@path/to/photo.jpg"
```

### 4. Obtener Token JWT
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

## 📊 Endpoints Principales

### Autenticación
- `POST /api/auth/login/` - Obtener token
- `POST /api/auth/register/` - Registrar usuario
- `POST /api/auth/logout/` - Cerrar sesión

### Empleados
- `GET /api/empleados/` - Listar empleados
- `POST /api/empleados/` - Crear empleado
- `POST /api/empleados/{id}/registrar-rostro/` - Registrar rostro

### Registros
- `POST /api/registros/marcar_entrada/` - Marcar entrada (sin auth)
- `POST /api/registros/marcar_salida/` - Marcar salida (sin auth)
- `GET /api/registros/` - Ver registros

### Horarios
- `GET /api/horarios/` - Listar horarios
- `POST /api/horarios/` - Crear horario
- `POST /api/horarios/bulk-create/` - Crear múltiples horarios

## 🔧 Configuración Actual

### Base de Datos
- **Tipo:** SQLite (para desarrollo)
- **Archivo:** `db.sqlite3`
- Para usar PostgreSQL, descomentar las líneas en `checador/settings.py`

### Reconocimiento Facial
- **Biblioteca:** face_recognition + OpenCV
- **Tolerancia:** 0.6 (ajustable en `registros/services/facial_recognition.py`)
- **Tamaño mínimo rostro:** 50x50 píxeles

## 📁 Estructura de Archivos

```
ChecadorLogincoV2/
├── db.sqlite3                 # Base de datos
├── media/                     # Archivos subidos
│   ├── rostros/              # Fotos de empleados
│   └── asistencias/          # Fotos de registros
├── manage.py                  # Django CLI
├── requirements.txt           # Dependencias
├── README.md                  # Documentación completa
└── QUICKSTART.md             # Esta guía
```

## 🧪 Probar el Sistema

### 1. Ver empleados en el admin
```
http://localhost:8000/admin/empleados/empleado/
```

### 2. Ver registros de asistencia
```
http://localhost:8000/admin/registros/registroasistencia/
```

### 3. Probar API (con Postman o curl)
```bash
# Obtener lista de empleados
curl http://localhost:8000/api/empleados/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## ⚠️ Notas Importantes

1. **Advertencia de face_recognition_models:** Es normal ver este warning al iniciar. El sistema funciona correctamente.

2. **PostgreSQL:** El sistema está configurado para SQLite por defecto. Para PostgreSQL:
   - Crear la base de datos `checador_db`
   - Descomentar las líneas de PostgreSQL en `settings.py`
   - Comentar las líneas de SQLite

3. **Producción:** Antes de deploy:
   - Cambiar `DEBUG = False`
   - Configurar `SECRET_KEY` segura
   - Usar PostgreSQL
   - Configurar archivos estáticos

## 🆘 Solución de Problemas

### El servidor no inicia
```bash
# Verificar que el venv esté activado
source .venvChecadorLoginco/bin/activate

# Reinstalar dependencias si es necesario
pip install -r requirements.txt
```

### Error de migraciones
```bash
# Aplicar migraciones pendientes
python manage.py migrate
```

### No puedo acceder al admin
- Verificar que el servidor esté corriendo
- Usar las credenciales: admin/admin123
- Crear nuevo superusuario si es necesario:
  ```bash
  python manage.py createsuperuser
  ```

## 📚 Documentación Completa

Ver `README.md` para documentación completa del proyecto.

## 🎉 ¡Todo Listo!

El sistema está completamente funcional y listo para:
- Registrar empleados
- Configurar horarios
- Marcar asistencias con reconocimiento facial
- Generar reportes
- Gestionar desde el panel de admin

¡Disfruta tu sistema de control de asistencias!
