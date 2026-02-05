#!/usr/bin/env python
"""
Test script to verify SendGrid email configuration.
Usage: python test_email_config.py <recipient_email>
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'checador.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail

def test_email_config():
    print("=== SendGrid Configuration Test ===")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"EMAIL_HOST_PASSWORD: {'*' * 20 if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    if not settings.EMAIL_HOST_PASSWORD:
        print("❌ ERROR: SENDGRID_API_KEY is not configured in .env")
        return False
    
    if len(sys.argv) < 2:
        print("Usage: python test_email_config.py <recipient_email>")
        return False
    
    recipient = sys.argv[1]
    print(f"📧 Sending test email to: {recipient}")
    print()
    
    try:
        send_mail(
            subject='Test Email - SendGrid Configuration',
            message='This is a test email to verify SendGrid configuration.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        print("✅ Email sent successfully!")
        print()
        print("Next steps:")
        print("1. Check your inbox (and spam folder)")
        print("2. If you don't receive it, verify sender in SendGrid:")
        print("   - Go to Settings → Sender Authentication")
        print("   - Verify domain or single sender email")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        print()
        print("Common issues:")
        print("1. Sender not verified in SendGrid")
        print("   Solution: Go to Settings → Sender Authentication")
        print("2. Invalid API key")
        print("   Solution: Generate new API key in SendGrid")
        print("3. API key doesn't have 'Mail Send' permission")
        print("   Solution: Recreate API key with 'Mail Send' access")
        return False

if __name__ == '__main__':
    test_email_config()
