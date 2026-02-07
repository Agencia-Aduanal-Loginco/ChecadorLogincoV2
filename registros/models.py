from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from checador.storage_backends import MediaStorage
from empleados.models import Empleado

# Zona horaria de México
MEXICO_TZ = ZoneInfo('America/Mexico_City')


def fecha_mexico():
    """Retorna la fecha actual en zona horaria de México"""
    return timezone.now().astimezone(MEXICO_TZ).date()


class RegistroAsistencia(models.Model):
    """Modelo para registrar asistencias de empleados"""

    TIPO_REGISTRO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]
    
    INCIDENCIA_CHOICES = [
        ('ninguna', 'Ninguna'),
        ('registro_incompleto', 'Registro Incompleto'),
        ('sin_entrada_comida', 'Falta entrada de comida'),
        ('sin_salida_comida', 'Falta salida de comida'),
        ('sin_salida', 'Falta salida final'),
    ]

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name='registros',
        verbose_name='Empleado'
    )
    fecha = models.DateField(
        default=fecha_mexico,
        verbose_name='Fecha'
    )
    hora_entrada = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Entrada'
    )
    hora_salida_comida = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Salida a Comida'
    )
    hora_entrada_comida = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Entrada de Comida'
    )
    hora_salida = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Salida'
    )
    horas_trabajadas = models.FloatField(
        default=0,
        verbose_name='Horas Trabajadas'
    )

    # Reconocimiento facial
    reconocimiento_facial = models.BooleanField(
        default=False,
        verbose_name='Reconocimiento Facial'
    )
    foto_registro = models.ImageField(
        storage=MediaStorage(),
        upload_to='asistencias/',
        null=True,
        blank=True,
        verbose_name='Foto de Registro'
    )
    confianza_reconocimiento = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Confianza del Reconocimiento',
        help_text='Porcentaje de confianza del reconocimiento facial'
    )

    # Ubicación (opcional para GPS)
    ubicacion = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Ubicación'
    )
    latitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Latitud'
    )
    longitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Longitud'
    )

    # Validación y estado
    retardo = models.BooleanField(
        default=False,
        verbose_name='Retardo'
    )
    justificado = models.BooleanField(
        default=False,
        verbose_name='Justificado'
    )
    incidencia = models.CharField(
        max_length=50,
        choices=INCIDENCIA_CHOICES,
        default='ninguna',
        verbose_name='Incidencia'
    )
    descripcion_incidencia = models.TextField(
        blank=True,
        verbose_name='Descripción de Incidencia'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Registro de Asistencia'
        verbose_name_plural = 'Registros de Asistencia'
        ordering = ['-fecha', '-hora_entrada']
        unique_together = ['empleado', 'fecha']

    def __str__(self):
        return f"{self.empleado.codigo_empleado} - {self.fecha}"

    def calcular_horas_trabajadas(self):
        """Calcula las horas trabajadas descontando el tiempo de comida"""
        if self.hora_entrada and self.hora_salida:
            entrada = datetime.combine(self.fecha, self.hora_entrada)
            salida = datetime.combine(self.fecha, self.hora_salida)

            # Si la salida es antes que la entrada, asumir que es el día siguiente
            if salida < entrada:
                salida += timedelta(days=1)

            diferencia = salida - entrada

            # Descontar tiempo de comida si se registró salida y entrada de comida
            if self.hora_salida_comida and self.hora_entrada_comida:
                salida_comida = datetime.combine(self.fecha, self.hora_salida_comida)
                entrada_comida = datetime.combine(self.fecha, self.hora_entrada_comida)
                if entrada_comida < salida_comida:
                    entrada_comida += timedelta(days=1)
                tiempo_comida = entrada_comida - salida_comida
                diferencia -= tiempo_comida

            self.horas_trabajadas = diferencia.total_seconds() / 3600
            return self.horas_trabajadas
        return 0

    def verificar_retardo(self):
        """Verifica si el empleado llego tarde segun su horario"""
        if not self.hora_entrada:
            return False

        from horarios.services import obtener_horario_del_dia
        horario_info = obtener_horario_del_dia(self.empleado, self.fecha)

        if horario_info:
            entrada_esperada = datetime.combine(self.fecha, horario_info['hora_entrada'])
            entrada_real = datetime.combine(self.fecha, self.hora_entrada)
            tolerancia = timedelta(minutes=horario_info['tolerancia_minutos'])

            self.retardo = entrada_real > (entrada_esperada + tolerancia)
            return self.retardo
        return False

    def save(self, *args, **kwargs):
        """Override save para calcular campos automáticamente"""
        if self.hora_entrada and self.hora_salida:
            self.calcular_horas_trabajadas()
        if self.hora_entrada:
            self.verificar_retardo()
        super().save(*args, **kwargs)

    @property
    def esta_completo(self):
        """Verifica si el registro tiene entrada y salida"""
        return bool(self.hora_entrada and self.hora_salida)

    def calcular_incidencias(self):
        """Calcula y establece incidencias basadas en el estado del registro"""
        # Si está justificado, no hay incidencia
        if self.justificado:
            self.incidencia = 'ninguna'
            self.descripcion_incidencia = ''
            return
        
        # Verificar si tiene entrada
        if not self.hora_entrada:
            self.incidencia = 'ninguna'  # Aún no ha empezado el día
            return
        
        # Verificar si tiene salida de comida pero no entrada de comida
        if self.hora_salida_comida and not self.hora_entrada_comida:
            self.incidencia = 'sin_entrada_comida'
            self.descripcion_incidencia = f'Salió a comer a las {self.hora_salida_comida} pero no registró entrada de comida'
            return
        
        # Verificar si tiene entrada de comida pero no salida final
        if self.hora_entrada_comida and not self.hora_salida:
            self.incidencia = 'sin_salida'
            self.descripcion_incidencia = f'Regresó de comer a las {self.hora_entrada_comida} pero no registró salida final'
            return
        
        # Verificar si tiene entrada pero no salida final
        if self.hora_entrada and not self.hora_salida:
            self.incidencia = 'sin_salida'
            self.descripcion_incidencia = f'Registró entrada a las {self.hora_entrada} pero no ha registrado salida'
            return
        
        # Si todo está completo, no hay incidencia
        self.incidencia = 'ninguna'
        self.descripcion_incidencia = ''
    
    def obtener_botones_disponibles(self, hora_actual=None):
        """Retorna lista de botones que deben estar habilitados segun el estado del registro"""
        if hora_actual is None:
            ahora_mexico = timezone.now().astimezone(MEXICO_TZ)
            hora_actual = ahora_mexico.time()

        from horarios.services import obtener_horario_del_dia
        horario_info = obtener_horario_del_dia(self.empleado, self.fecha)

        botones = []

        # Sin entrada registrada -> solo entrada disponible
        if not self.hora_entrada:
            return ['entrada']

        # Con entrada, sin salida a comida
        if self.hora_entrada and not self.hora_salida_comida:
            if horario_info and horario_info['tiene_comida']:
                obj = horario_info['objeto']
                if hasattr(obj, 'esta_en_horario_comida') and obj.esta_en_horario_comida(hora_actual):
                    botones.extend(['salida_comida', 'salida'])
                else:
                    botones.append('salida')
            else:
                botones.append('salida')
            return botones

        # Con salida a comida, sin entrada de comida
        if self.hora_salida_comida and not self.hora_entrada_comida:
            return ['entrada_comida']

        # Con entrada de comida, sin salida final
        if self.hora_entrada_comida and not self.hora_salida:
            return ['salida']

        # Con salida final registrada -> ya no hay mas botones
        if self.hora_salida:
            return []

        return []
    
    @property
    def tiempo_trabajado_str(self):
        """Retorna las horas trabajadas en formato legible"""
        if self.horas_trabajadas:
            horas = int(self.horas_trabajadas)
            minutos = int((self.horas_trabajadas - horas) * 60)
            return f"{horas}h {minutos}m"
        return "0h 0m"
