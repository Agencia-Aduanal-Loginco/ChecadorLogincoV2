from django.db import models
from django.core.exceptions import ValidationError
from empleados.models import Empleado


class TipoHorario(models.Model):
    """Plantilla de horario reutilizable con nombre"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    codigo = models.CharField(max_length=20, unique=True, verbose_name='Codigo')
    descripcion = models.TextField(blank=True, verbose_name='Descripcion')
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        verbose_name='Color (hex)',
        help_text='Color para identificar el horario en la vista de asignacion'
    )

    hora_entrada = models.TimeField(verbose_name='Hora de Entrada')
    hora_salida = models.TimeField(verbose_name='Hora de Salida')
    tolerancia_minutos = models.IntegerField(
        default=10,
        verbose_name='Tolerancia (minutos)',
        help_text='Minutos de tolerancia para entrada'
    )

    # Comida
    tiene_comida = models.BooleanField(default=True, verbose_name='Tiene comida')
    hora_inicio_comida = models.TimeField(
        null=True, blank=True, verbose_name='Hora inicio comida'
    )
    hora_fin_comida = models.TimeField(
        null=True, blank=True, verbose_name='Hora fin comida'
    )

    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tipo de Horario'
        verbose_name_plural = 'Tipos de Horario'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.hora_entrada} - {self.hora_salida})"

    def clean(self):
        if self.hora_salida and self.hora_entrada and self.hora_salida <= self.hora_entrada:
            raise ValidationError('La hora de salida debe ser posterior a la hora de entrada.')

    def esta_en_horario_comida(self, hora_actual):
        if not self.tiene_comida or not self.hora_inicio_comida or not self.hora_fin_comida:
            return False
        return self.hora_inicio_comida <= hora_actual <= self.hora_fin_comida


class AsignacionHorario(models.Model):
    """Asignacion de un tipo de horario a un empleado en una fecha especifica"""
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name='asignaciones_horario',
        verbose_name='Empleado'
    )
    fecha = models.DateField(verbose_name='Fecha')
    tipo_horario = models.ForeignKey(
        TipoHorario,
        on_delete=models.CASCADE,
        related_name='asignaciones',
        verbose_name='Tipo de Horario'
    )

    notas = models.CharField(max_length=255, blank=True)
    creado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Creado por'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignacion de Horario'
        verbose_name_plural = 'Asignaciones de Horario'
        unique_together = ['empleado', 'fecha']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['empleado', 'fecha']),
        ]

    def __str__(self):
        return f"{self.empleado.codigo_empleado} - {self.fecha} - {self.tipo_horario.nombre}"


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
    
    # Configuración de comida
    tiene_comida = models.BooleanField(
        default=True,
        verbose_name='Tiene horario de comida',
        help_text='Indica si el empleado tiene periodo de comida'
    )
    hora_inicio_comida = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora inicio de comida',
        help_text='Hora a partir de la cual puede salir a comer (ej: 13:00)'
    )
    hora_fin_comida = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora fin de comida',
        help_text='Hora límite para regresar de comer (ej: 16:00)'
    )
    
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
    
    def esta_en_horario_comida(self, hora_actual):
        """Verifica si la hora actual está dentro del horario de comida"""
        if not self.tiene_comida or not self.hora_inicio_comida or not self.hora_fin_comida:
            return False
        return self.hora_inicio_comida <= hora_actual <= self.hora_fin_comida
    
    @property
    def horas_dia(self):
        """Calcula las horas de trabajo del día"""
        from datetime import datetime, timedelta
        entrada = datetime.combine(datetime.today(), self.hora_entrada)
        salida = datetime.combine(datetime.today(), self.hora_salida)
        diferencia = salida - entrada
        return diferencia.total_seconds() / 3600
