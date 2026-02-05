# Configuración de SendGrid para el Sistema de Checador

Este documento explica cómo configurar SendGrid para enviar emails desde el sistema de checador.

## 📋 Requisitos Previos

1. Cuenta activa en [SendGrid](https://sendgrid.com/)
2. API Key de SendGrid generada
3. Email remitente verificado en SendGrid

---

## 🔑 Paso 1: Obtener API Key de SendGrid

### 1.1 Crear cuenta o iniciar sesión
- Visita [https://sendgrid.com/](https://sendgrid.com/)
- Crea una cuenta gratuita o inicia sesión

### 1.2 Generar API Key
1. Ve a **Settings** → **API Keys**
2. Haz clic en **Create API Key**
3. Dale un nombre descriptivo (ej: "Checador Loginco Production")
4. Selecciona **Full Access** o **Restricted Access** con permisos de envío de mail
5. Haz clic en **Create & View**
6. **¡IMPORTANTE!** Copia la API Key inmediatamente (solo se muestra una vez)
   - Formato: `SG.xxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyy`

---

## ✉️ Paso 2: Verificar Email Remitente

SendGrid requiere que verifiques el email que usarás como remitente.

### 2.1 Verificación de Sender Identity
1. Ve a **Settings** → **Sender Authentication**
2. Elige una de las opciones:
   - **Single Sender Verification** (más rápido, recomendado para desarrollo)
   - **Domain Authentication** (recomendado para producción)

### 2.2 Single Sender Verification (método rápido)
1. Haz clic en **Verify a Single Sender**
2. Completa el formulario:
   - **From Name**: Sistema de Checador
   - **From Email Address**: notificaciones@loginco.com.mx (o el que prefieras)
   - **Reply To**: (mismo email o uno diferente)
   - Completa los demás campos
3. Haz clic en **Create**
4. Revisa tu email y haz clic en el link de verificación

### 2.3 Domain Authentication (recomendado para producción)
1. Haz clic en **Authenticate Your Domain**
2. Selecciona tu DNS provider
3. Sigue las instrucciones para agregar registros DNS
4. Espera la verificación (puede tomar hasta 48 horas)

---

## ⚙️ Paso 3: Configurar Variables de Entorno

### 3.1 Agregar API Key al archivo .env
1. Abre o crea el archivo `.env` en la raíz del proyecto:
   ```bash
   nano .env  # o usa tu editor favorito
   ```

2. Agrega las siguientes líneas:
   ```bash
   # SendGrid Email Configuration
   SENDGRID_API_KEY=SG.tu_api_key_completa_aqui
   DEFAULT_FROM_EMAIL=Sistema de Checador <notificaciones@loginco.com.mx>
   ```

3. **¡IMPORTANTE!** Asegúrate de que el email en `DEFAULT_FROM_EMAIL` coincida con el que verificaste en SendGrid.

### 3.2 Verificar que .env esté en .gitignore
```bash
# Verificar que .env NO se suba a git
cat .gitignore | grep ".env"
```

Si no está, agrégalo:
```bash
echo ".env" >> .gitignore
```

---

## 🧪 Paso 4: Probar la Configuración

### 4.1 Ejecutar script de prueba
```bash
# Asegúrate de estar en el entorno virtual
source .venvChecadorLoginco/bin/activate

# Ejecutar prueba (reemplaza con tu email)
python test_sendgrid.py tu_email@ejemplo.com
```

### 4.2 Resultado esperado
Si todo está bien configurado, deberías ver:
```
🔍 Verificando configuración de SendGrid...

✅ EMAIL_BACKEND: django.core.mail.backends.smtp.EmailBackend
✅ EMAIL_HOST: smtp.sendgrid.net
✅ EMAIL_PORT: 587
✅ EMAIL_USE_TLS: True
✅ EMAIL_HOST_USER: apikey
✅ EMAIL_HOST_PASSWORD: ***configurada***
✅ DEFAULT_FROM_EMAIL: Sistema de Checador <notificaciones@loginco.com.mx>

📧 Enviando email de prueba a: tu_email@ejemplo.com
✅ Email enviado exitosamente!
   Revisa la bandeja de entrada de: tu_email@ejemplo.com

✅ Prueba completada exitosamente!
```

### 4.3 Verificar email recibido
1. Revisa tu bandeja de entrada
2. Si no lo ves, revisa la carpeta de SPAM
3. El asunto debería ser: "Prueba de SendGrid - Sistema de Checador"

---

## 🐛 Solución de Problemas

### Error: "API Key no configurada"
```
❌ EMAIL_HOST_PASSWORD: ❌ NO CONFIGURADA
```
**Solución**: Verifica que agregaste `SENDGRID_API_KEY` en tu archivo `.env`

### Error: "Authentication failed"
```
SMTPAuthenticationError: (535, b'Authentication failed: Bad username / password')
```
**Soluciones**:
1. Verifica que la API Key sea correcta (copia/pega completa)
2. Genera una nueva API Key en SendGrid
3. Asegúrate de que la API Key tenga permisos de envío de mail

### Error: "Sender address rejected"
```
SMTPSenderRefused: (550, b'The from address does not match a verified Sender Identity')
```
**Solución**: 
1. El email en `DEFAULT_FROM_EMAIL` debe estar verificado en SendGrid
2. Ve a SendGrid → Settings → Sender Authentication
3. Verifica que el email esté en la lista y marcado como "Verified"

### Email no llega
**Revisa**:
1. Carpeta de SPAM
2. SendGrid Dashboard → Activity → busca el email
3. Verifica que no haya errores en los logs de SendGrid

### Error de conexión de red
```
SMTPServerDisconnected: Connection unexpectedly closed
```
**Soluciones**:
1. Verifica tu conexión a internet
2. Comprueba que el puerto 587 no esté bloqueado por firewall
3. Intenta con el puerto 465 (cambia en settings.py)

---

## 📊 Monitoreo en SendGrid

### Dashboard de SendGrid
1. Ve a [https://app.sendgrid.com/](https://app.sendgrid.com/)
2. **Dashboard** → Muestra estadísticas generales
3. **Activity** → Ver emails enviados, entregas, rebotes, etc.
4. **Statistics** → Métricas detalladas

### Límites del plan gratuito
- **100 emails/día** (Free plan)
- Para más, considera actualizar a un plan de pago

---

## 🚀 Configuración para Producción

### Variables de entorno en DigitalOcean/Render
1. Ve a tu aplicación en DigitalOcean App Platform o Render
2. Agrega las variables de entorno:
   ```
   SENDGRID_API_KEY=tu_api_key_de_produccion
   DEFAULT_FROM_EMAIL=Sistema de Checador <notificaciones@loginco.com.mx>
   ```
3. Redeploy la aplicación

### Domain Authentication (recomendado)
Para producción, es altamente recomendable configurar Domain Authentication:
- Mejora la deliverability (tasa de entrega)
- Evita que los emails caigan en SPAM
- Da más credibilidad a tus emails

---

## 📝 Uso en el Código

El sistema ya está configurado para usar SendGrid. Los reportes se envían automáticamente desde:

```python path=reportes/services/generador_email.py start=10
def enviar_reporte(tipo_reporte, datos, destinatarios, archivo_excel=None, asunto_custom=None):
    """Envia reporte por email con SendGrid."""
    # ... código para enviar emails
```

Para enviar emails manualmente:
```python path=null start=null
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

---

## 🔗 Enlaces Útiles

- [SendGrid Dashboard](https://app.sendgrid.com/)
- [SendGrid Documentation](https://docs.sendgrid.com/)
- [Django Email Documentation](https://docs.djangoproject.com/en/5.0/topics/email/)
- [SendGrid API Keys](https://app.sendgrid.com/settings/api_keys)
- [SendGrid Sender Authentication](https://app.sendgrid.com/settings/sender_auth)

---

## ✅ Checklist de Configuración

- [ ] Cuenta de SendGrid creada
- [ ] API Key generada y copiada
- [ ] Email remitente verificado en SendGrid
- [ ] Variable `SENDGRID_API_KEY` agregada a `.env`
- [ ] Variable `DEFAULT_FROM_EMAIL` configurada
- [ ] Script de prueba ejecutado exitosamente
- [ ] Email de prueba recibido
- [ ] `.env` agregado a `.gitignore`

---

**¡Listo!** Tu sistema de checador ahora puede enviar emails a través de SendGrid.
