from datetime import time
from django.db import models


class ConfiguracionReporte(models.Model):
    """Configuracion global de reportes"""
    TIPO_REPORTE_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
    ]

    DIA_ENVIO_CHOICES = [
        (5, 'Viernes'),
        (6, 'Sabado'),
    ]

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_REPORTE_CHOICES,
        unique=True,
        verbose_name='Tipo de Reporte'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    hora_envio = models.TimeField(
        default=time(11, 50),
        verbose_name='Hora de envio'
    )
    asunto_email = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Asunto del email',
        help_text='Dejar vacio para usar asunto por defecto'
    )

    # Solo para reporte semanal
    dia_envio_semanal = models.IntegerField(
        null=True, blank=True,
        choices=DIA_ENVIO_CHOICES,
        verbose_name='Dia de envio (semanal)',
        help_text='Solo aplica para reporte semanal'
    )

    incluir_excel = models.BooleanField(
        default=False,
        verbose_name='Incluir anexo Excel',
        help_text='El reporte diario no incluye Excel por defecto'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuracion de Reporte'
        verbose_name_plural = 'Configuraciones de Reportes'

    def __str__(self):
        return f"Reporte {self.get_tipo_display()} - {'Activo' if self.activo else 'Inactivo'}"


class DestinatarioReporte(models.Model):
    """Destinatarios de reportes por email"""
    configuracion = models.ForeignKey(
        ConfiguracionReporte,
        on_delete=models.CASCADE,
        related_name='destinatarios'
    )
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    email = models.EmailField(verbose_name='Email')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Destinatario'
        verbose_name_plural = 'Destinatarios'
        unique_together = ['configuracion', 'email']

    def __str__(self):
        return f"{self.nombre} <{self.email}>"


class LogReporte(models.Model):
    """Log de reportes enviados"""
    ESTADO_CHOICES = [
        ('enviado', 'Enviado'),
        ('error', 'Error'),
        ('parcial', 'Parcial'),
    ]

    tipo_reporte = models.CharField(max_length=20, verbose_name='Tipo')
    fecha_inicio_rango = models.DateField(verbose_name='Fecha inicio')
    fecha_fin_rango = models.DateField(verbose_name='Fecha fin')
    destinatarios_enviados = models.IntegerField(default=0, verbose_name='Destinatarios')
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        verbose_name='Estado'
    )
    error_detalle = models.TextField(blank=True, verbose_name='Detalle de error')
    fecha_envio = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de envio')

    class Meta:
        verbose_name = 'Log de Reporte'
        verbose_name_plural = 'Logs de Reportes'
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"{self.tipo_reporte} - {self.fecha_envio.strftime('%Y-%m-%d %H:%M')} - {self.estado}"
