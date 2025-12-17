# Guía de Despliegue - Digital Ocean App Platform

## Problema Resuelto: ImportError libGL.so.1

El error `ImportError: libGL.so.1: cannot open shared object file` ocurre porque OpenCV requiere dependencias del sistema que no están disponibles por defecto en los contenedores.

## Archivos Creados para el Despliegue

### 1. `Aptfile`
Especifica las dependencias del sistema Linux necesarias para OpenCV y dlib:
- libgl1-mesa-glx
- libglib2.0-0
- libsm6
- libxext6
- libxrender-dev
- libgomp1
- cmake

### 2. `Procfile`
Define cómo iniciar la aplicación en producción con Gunicorn:
```
web: gunicorn checador.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 120
```

### 3. `runtime.txt`
Especifica la versión de Python:
```
python-3.12.0
```

### 4. `build.sh`
Script de construcción que instala dependencias del sistema y prepara la aplicación.

### 5. `app.yaml`
Configuración específica para Digital Ocean App Platform.

## Pasos para Desplegar en Digital Ocean

### Opción 1: Usar la interfaz de Digital Ocean

1. **Ir a App Platform** en Digital Ocean
2. **Crear Nueva App**
3. **Conectar tu repositorio de GitHub**
4. **Configurar las siguientes variables de entorno:**
   ```
   DEBUG=False
   SECRET_KEY=tu-clave-secreta-super-segura-aqui
   ALLOWED_HOSTS=tu-app.ondigitalocean.app
   
   # Base de datos PostgreSQL (provista por Digital Ocean)
   DATABASE_URL=postgresql://...
   
   # JWT Settings
   JWT_ACCESS_TOKEN_LIFETIME=60
   JWT_REFRESH_TOKEN_LIFETIME=1440
   ```

5. **En "Build Command"**, usar:
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
   ```

6. **En "Run Command"**, usar:
   ```bash
   gunicorn checador.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 120
   ```

7. **Agregar una base de datos PostgreSQL** desde el panel de Digital Ocean

8. **Configurar Health Check**:
   - Path: `/admin/login/`
   - Port: 8080

### Opción 2: Usar doctl CLI

```bash
# Instalar doctl
brew install doctl  # macOS
# o snap install doctl  # Linux

# Autenticarse
doctl auth init

# Desplegar usando app.yaml
doctl apps create --spec app.yaml

# Ver logs
doctl apps logs <app-id>
```

## Configuración de Base de Datos PostgreSQL

Si usas una base de datos PostgreSQL provista por Digital Ocean, actualiza tu `.env` o variables de entorno:

```python
# En settings.py, agrega al final:
import dj_database_url

if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
```

Y agrega `dj-database-url` a `requirements.txt`:
```
dj-database-url==2.2.0
```

## Solución al Error de OpenCV

El `Aptfile` instala automáticamente las dependencias del sistema necesarias. Digital Ocean App Platform detecta este archivo y ejecuta:

```bash
apt-get update
apt-get install -y <paquetes-del-Aptfile>
```

Esto resuelve el error `libGL.so.1: cannot open shared object file`.

## Verificación Post-Despliegue

1. **Verificar que la app esté corriendo:**
   ```bash
   curl https://tu-app.ondigitalocean.app/admin/login/
   ```

2. **Crear superusuario:**
   ```bash
   # Desde la consola de Digital Ocean
   python manage.py createsuperuser
   ```

3. **Verificar logs:**
   ```bash
   doctl apps logs <app-id> --follow
   ```

## Problemas Comunes

### 1. Error 502 Bad Gateway
- Verifica que el puerto sea 8080
- Revisa logs: `doctl apps logs <app-id>`

### 2. Static files no se cargan
- Asegúrate de que `whitenoise` esté instalado
- Ejecuta `python manage.py collectstatic`

### 3. Error de CSRF
- Agrega el dominio a `ALLOWED_HOSTS`
- Configura `CSRF_TRUSTED_ORIGINS`

### 4. Error de importación de OpenCV
- Verifica que el `Aptfile` esté en la raíz del proyecto
- Verifica que las dependencias se instalaron: revisa logs de build

## Monitoreo

- **Logs**: `doctl apps logs <app-id> --follow`
- **Métricas**: Panel de Digital Ocean
- **Alertas**: Configurar en Digital Ocean

## Rollback

Si algo sale mal:
```bash
# Listar deployments
doctl apps list-deployments <app-id>

# Rollback a deployment anterior
doctl apps rollback <app-id> <deployment-id>
```

## Seguridad en Producción

✅ HTTPS habilitado automáticamente
✅ `DEBUG=False`
✅ `SECRET_KEY` segura en variables de entorno
✅ CORS configurado correctamente
✅ CSRF protection habilitado
✅ Whitenoise para servir archivos estáticos

## Costos Estimados

- **Basic Plan**: ~$5-12/mes (según recursos)
- **PostgreSQL Database**: ~$7/mes (opcional)
- **Storage**: Incluido en plan básico

## Soporte

Si tienes problemas, revisa:
1. Logs de build: Busca errores de instalación
2. Logs de runtime: Busca errores de la aplicación
3. Variables de entorno: Verifica que todas estén configuradas
4. Health checks: Asegúrate de que el endpoint responda

## Comandos Útiles

```bash
# Ver información de la app
doctl apps get <app-id>

# Ver variables de entorno
doctl apps spec get <app-id>

# Reiniciar app
doctl apps restart <app-id>

# Ver builds
doctl apps list-builds <app-id>
```
