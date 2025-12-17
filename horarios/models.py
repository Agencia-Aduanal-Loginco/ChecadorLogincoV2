from django.db import models
from django.core.exceptions import ValidationError
from empleados.models import Empleado


class Horario(models.Model):
    """Modelo para definir horarios de trabajo de empleados"""
    
    DIAS_SEMANA = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
        (6, 'Sábado'),
        (7, 'Domingo'),
    ]
    
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name='horarios',
        verbose_name='Empleado'
    )
    dia_semana = models.IntegerField(
        choices=DIAS_SEMANA,
        verbose_name='Día de la Semana'
    )
    hora_entrada = models.TimeField(verbose_name='Hora de Entrada')
    hora_salida = models.TimeField(verbose_name='Hora de Salida')
    
    # Configuración adicional
    tolerancia_minutos = models.IntegerField(
        default=10,
        verbose_name='Tolerancia (minutos)',
        help_text='Minutos de tolerancia para entrada'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'
        ordering = ['empleado', 'dia_semana']
        unique_together = ['empleado', 'dia_semana']
    
    def __str__(self):
        return f"{self.empleado.codigo_empleado} - {self.get_dia_semana_display()}: {self.hora_entrada} - {self.hora_salida}"
    
    def clean(self):
        """Validación personalizada"""
        if self.hora_salida <= self.hora_entrada:
            raise ValidationError('La hora de salida debe ser posterior a la hora de entrada.')
    
    @property
    def horas_dia(self):
        """Calcula las horas de trabajo del día"""
        from datetime import datetime, timedelta
        entrada = datetime.combine(datetime.today(), self.hora_entrada)
        salida = datetime.combine(datetime.today(), self.hora_salida)
        diferencia = salida - entrada
        return diferencia.total_seconds() / 3600
