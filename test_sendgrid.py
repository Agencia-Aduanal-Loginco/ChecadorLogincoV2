#!/usr/bin/env python
"""
Script de prueba para verificar la configuración de SendGrid.
Uso: python test_sendgrid.py <email_destino>
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'checador.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings


def test_sendgrid_connection():
    """Verifica que la configuración de SendGrid esté correcta."""
    print("🔍 Verificando configuración de SendGrid...\n")
    
    # Verificar que las variables estén configuradas
    checks = [
        ("EMAIL_BACKEND", settings.EMAIL_BACKEND),
        ("EMAIL_HOST", settings.EMAIL_HOST),
        ("EMAIL_PORT", settings.EMAIL_PORT),
        ("EMAIL_USE_TLS", settings.EMAIL_USE_TLS),
        ("EMAIL_HOST_USER", settings.EMAIL_HOST_USER),
        ("EMAIL_HOST_PASSWORD", "***configurada***" if settings.EMAIL_HOST_PASSWORD else "❌ NO CONFIGURADA"),
        ("DEFAULT_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL),
    ]
    
    all_ok = True
    for name, value in checks:
        if name == "EMAIL_HOST_PASSWORD":
            status = "✅" if settings.EMAIL_HOST_PASSWORD else "❌"
            print(f"{status} {name}: {value}")
            if not settings.EMAIL_HOST_PASSWORD:
                all_ok = False
        else:
            print(f"✅ {name}: {value}")
    
    if not all_ok:
        print("\n❌ Error: SENDGRID_API_KEY no está configurada en el archivo .env")
        print("   Por favor, agrega tu API key de SendGrid en el archivo .env:")
        print("   SENDGRID_API_KEY=tu_api_key_aqui")
        return False
    
    return True


def send_test_email(recipient_email):
    """Envía un email de prueba."""
    try:
        print(f"\n📧 Enviando email de prueba a: {recipient_email}")
        
        send_mail(
            subject='Prueba de SendGrid - Sistema de Checador',
            message='Este es un email de prueba del sistema de checador. Si recibes este mensaje, la configuración de SendGrid está funcionando correctamente.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        print("✅ Email enviado exitosamente!")
        print(f"   Revisa la bandeja de entrada de: {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar email: {str(e)}")
        print("\nPosibles causas:")
        print("  1. API Key inválida o expirada")
        print("  2. Email remitente no verificado en SendGrid")
        print("  3. Problemas de conectividad de red")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ Error: Debes proporcionar un email de destino")
        print(f"Uso: python {sys.argv[0]} <email_destino>")
        print(f"Ejemplo: python {sys.argv[0]} tu_email@ejemplo.com")
        sys.exit(1)
    
    recipient = sys.argv[1]
    
    # Verificar configuración
    if not test_sendgrid_connection():
        sys.exit(1)
    
    # Enviar email de prueba
    if send_test_email(recipient):
        print("\n✅ Prueba completada exitosamente!")
        sys.exit(0)
    else:
        print("\n❌ La prueba falló. Revisa la configuración.")
        sys.exit(1)
