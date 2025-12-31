# Deployment en Digital Ocean App Platform

Este proyecto ahora usa Docker para despliegue en Digital Ocean, lo que resuelve los problemas de compilación de `dlib`.

## Requisitos Previos

1. Cuenta en Digital Ocean
2. Repositorio conectado a Digital Ocean App Platform
3. Variables de entorno configuradas

## Configuración

### 1. Variables de Entorno Requeridas

En el dashboard de Digital Ocean App Platform, configura las siguientes variables de entorno:

```bash
# Django
DEBUG=False
SECRET_KEY=tu-secret-key-aqui
DJANGO_SETTINGS_MODULE=checador.settings
PYTHONUNBUFFERED=1

# Base de datos (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# JWT
ACCESS_TOKEN_LIFETIME_MINUTES=60
REFRESH_TOKEN_LIFETIME_MINUTES=1440

# CORS (opcional, para frontend separado)
CORS_ALLOWED_ORIGINS=https://tu-frontend.com

# Media y Static
STATIC_URL=/static/
MEDIA_URL=/media/
```

### 2. Configuración de App Platform

El archivo `app.yaml` está configurado para usar Docker:

```yaml
name: checador-loginco
services:
- name: web
  dockerfile_path: Dockerfile
  github:
    branch: main
    deploy_on_push: true
  http_port: 8080
  instance_count: 1
  instance_size_slug: basic-xxs
```

### 3. Base de Datos

Digital Ocean puede provisionar automáticamente una base de datos PostgreSQL:

1. En el dashboard, ve a "Database"
2. Crea un nuevo PostgreSQL cluster (o usa uno existente)
3. En tu app, añade la base de datos en la sección "Resources"
4. Digital Ocean automáticamente configurará `DATABASE_URL`

## Proceso de Deployment

### Opción 1: Deploy Automático (Recomendado)

1. Haz push de los cambios a la rama `main`:
   ```bash
   git add .
   git commit -m "Configure Docker deployment"
   git push origin main
   ```

2. Digital Ocean detectará automáticamente los cambios y comenzará el build

### Opción 2: Deploy Manual

1. En el dashboard de Digital Ocean App Platform
2. Selecciona tu app
3. Click en "Deploy"
4. Selecciona la rama `main`

## Dockerfile

El proyecto incluye un `Dockerfile` optimizado que:

- ✅ Usa Python 3.12 slim (menor tamaño)
- ✅ Instala todas las dependencias del sistema para dlib y OpenCV
- ✅ Compila dlib correctamente con soporte completo
- ✅ Instala todas las dependencias de Python
- ✅ Ejecuta collectstatic automáticamente
- ✅ Ejecuta migraciones en el inicio

## Verificación del Deployment

1. **Build exitoso**: Verifica que el build se complete sin errores en los logs
2. **Health check**: Digital Ocean verifica automáticamente `/admin/login/`
3. **Prueba manual**: Accede a tu URL de Digital Ocean y verifica:
   - Panel de admin: `https://tu-app.ondigitalocean.app/admin/`
   - API endpoints: `https://tu-app.ondigitalocean.app/api/`

## Troubleshooting

### Error: "dlib failed to build"

✅ **Solucionado**: Ahora usamos Docker que tiene todas las herramientas de compilación

### Error: "collectstatic failed"

Verifica que `STATIC_ROOT` esté configurado en `settings.py`:
```python
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

### Error: "Database connection failed"

1. Verifica que `DATABASE_URL` esté configurado correctamente
2. Verifica que la base de datos esté conectada en "Resources"
3. Verifica que el cluster de base de datos esté activo

### Error: "Module not found"

Verifica que todas las dependencias estén en `requirements.txt` y que el build haya completado exitosamente

## Optimizaciones

### Reducir Tiempo de Build

El Dockerfile ya está optimizado:
- Usa cache de capas de Docker
- Instala dependencias antes de copiar código fuente
- Usa `--no-cache-dir` en pip

### Reducir Costos

- **Instance size**: Comienza con `basic-xxs` y escala según necesidad
- **Workers**: Configurado con 2 workers de Gunicorn
- **Database**: Usa el tier más pequeño que soporte tu carga

### Monitoreo

Digital Ocean App Platform proporciona:
- Logs en tiempo real
- Métricas de CPU y memoria
- Alertas automáticas
- Health checks

## Comandos Útiles

### Ver logs en vivo
```bash
doctl apps logs <app-id> --follow
```

### Ejecutar migraciones manualmente
Las migraciones se ejecutan automáticamente en cada deploy, pero si necesitas ejecutarlas manualmente:

1. Usa la consola de Digital Ocean
2. O conéctate via SSH si está habilitado

### Revertir a versión anterior
En el dashboard:
1. Ve a "Deployments"
2. Selecciona el deployment anterior
3. Click en "Redeploy"

## Archivos de Configuración

- `Dockerfile` - Configuración de la imagen Docker
- `.dockerignore` - Archivos excluidos del build
- `app.yaml` - Configuración de Digital Ocean App Platform
- `requirements.txt` - Dependencias de Python

## Notas Importantes

1. **No uses buildpacks**: Este proyecto requiere Docker debido a las dependencias de compilación de dlib
2. **Media files**: Considera usar Spaces (S3-compatible) de Digital Ocean para archivos media en producción
3. **Static files**: WhiteNoise está configurado para servir archivos estáticos
4. **Secrets**: NUNCA hagas commit de `.env` o secretos al repositorio

## Soporte

Para más información sobre Digital Ocean App Platform:
- [Documentación oficial](https://docs.digitalocean.com/products/app-platform/)
- [Docker en App Platform](https://docs.digitalocean.com/products/app-platform/reference/dockerfile/)
