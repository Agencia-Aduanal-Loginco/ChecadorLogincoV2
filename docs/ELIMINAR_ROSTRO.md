# Eliminación de Rostros Faciales

## Descripción
Funcionalidad para eliminar registros faciales incorrectos y permitir re-registro cuando el rostro capturado no corresponde al empleado correcto.

## Casos de uso
- Cuando se registró el rostro de otra persona por error
- Cuando la foto capturada tiene mala calidad y causa falsos negativos
- Cuando se necesita actualizar completamente el registro facial

## Implementación

### Backend

#### Modelo: `Empleado.eliminar_rostro()`
```python
def eliminar_rostro(self):
    """Elimina el registro facial del empleado"""
    self.embedding_rostro = None
    if self.foto_rostro:
        self.foto_rostro.delete(save=False)
        self.foto_rostro = None
    self.save()
```

#### Endpoints API

##### REST API (requiere JWT)
- **URL**: `/api/empleados/{id}/eliminar-rostro/`
- **Método**: POST
- **Autenticación**: JWT Token
- **Respuesta exitosa**:
```json
{
    "success": true,
    "message": "Registro facial eliminado exitosamente. Puedes registrar un nuevo rostro.",
    "empleado": { ... }
}
```

##### Session API (usa cookies de Django)
- **URL**: `/api/empleados/{id}/eliminar-rostro-session/`
- **Método**: POST
- **Autenticación**: Session (login_required)
- **Permisos**: Solo staff
- **Respuesta exitosa**:
```json
{
    "success": true,
    "message": "Registro facial eliminado exitosamente. Puedes registrar un nuevo rostro."
}
```

### Frontend

#### Página de Registro de Rostro
En la página `/api/empleados/{id}/registrar-rostro-web/`:

1. **Botón de eliminación** (icono de basura) en el header
   - Solo visible cuando hay rostro registrado
   - Requiere confirmación antes de eliminar
   - Actualiza la UI automáticamente después de eliminar

2. **Advertencia informativa**
   - Notifica al usuario si ya existe un rostro registrado
   - Indica cómo eliminar el rostro actual

#### Django Admin

1. **Columna "Gestión de Rostro"** en lista de empleados:
   - Muestra estado: "Activo" con botón "Ver/Actualizar" si hay rostro
   - Muestra botón "Registrar Rostro" si no hay rostro

2. **Acción masiva**: "Eliminar rostros faciales de empleados seleccionados"
   - Permite eliminar múltiples rostros a la vez
   - Muestra contador de rostros eliminados

## Flujo de uso

### Desde la interfaz web:

1. **Detectar error en registro**:
   - Ir a Admin → Empleados → Seleccionar empleado
   - Click en "Ver/Actualizar" en columna "Gestión de Rostro"

2. **Eliminar rostro incorrecto**:
   - Click en icono de basura (🗑️) junto al badge "Rostro Registrado"
   - Confirmar eliminación en el diálogo
   - Esperar mensaje de éxito

3. **Registrar nuevo rostro**:
   - El badge cambiará a "Sin Rostro"
   - Activar cámara
   - Capturar nuevo rostro
   - Registrar

### Desde el admin (eliminación masiva):

1. Admin → Empleados
2. Seleccionar empleados con rostros incorrectos
3. En "Acciones": Seleccionar "Eliminar rostros faciales de empleados seleccionados"
4. Click en "Ir"
5. Confirmar la acción

### Desde la API:

```bash
# Con JWT
curl -X POST https://tu-dominio.com/api/empleados/123/eliminar-rostro/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Con sesión
curl -X POST https://tu-dominio.com/api/empleados/123/eliminar-rostro-session/ \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  --cookie "sessionid=YOUR_SESSION_ID"
```

## Seguridad

- **Permisos REST API**: Requiere autenticación JWT
- **Permisos Session API**: Solo usuarios staff (`is_staff=True`)
- **Confirmación en UI**: Diálogo de confirmación antes de eliminar
- **No se puede recuperar**: La eliminación es permanente (sin papelera)

## Logs y auditoría

Para auditar eliminaciones de rostros, se recomienda:
1. Usar señales de Django para registrar eliminaciones
2. Crear un modelo de auditoría (opcional)

Ejemplo de señal:
```python
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Empleado)
def log_rostro_eliminado(sender, instance, **kwargs):
    if instance.pk:
        old = Empleado.objects.get(pk=instance.pk)
        if old.tiene_rostro_registrado and not instance.tiene_rostro_registrado:
            print(f"Rostro eliminado: {instance.codigo_empleado}")
```

## Notas importantes

- Al eliminar, se borran tanto `embedding_rostro` (encoding) como `foto_rostro` (archivo)
- El archivo físico se elimina del storage (local o S3)
- Después de eliminar, el empleado puede volver a registrar su rostro inmediatamente
- No hay límite de veces que se puede eliminar y volver a registrar
