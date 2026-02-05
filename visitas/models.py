from django.db import models
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

from checador.storage_backends import MediaStorage


class MotivoVisita(models.Model):
    """Modelo para motivos de visita"""

    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripcion'
    )
    requiere_autorizacion = models.BooleanField(
        default=True,
        verbose_name='Requiere Autorizacion'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Motivo de Visita'
        verbose_name_plural = 'Motivos de Visita'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Visita(models.Model):
    """Modelo para registro de visitas"""

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('autorizado', 'Autorizado'),
        ('en_sitio', 'En Sitio'),
        ('finalizado', 'Finalizado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
        ('no_show', 'No Se Presento'),
    ]

    IDENTIFICACION_CHOICES = [
        ('ine', 'INE/IFE'),
        ('pasaporte', 'Pasaporte'),
        ('licencia', 'Licencia de Conducir'),
        ('otro', 'Otro'),
    ]

    # Identificacion unica
    codigo_visita = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='Codigo de Visita'
    )

    # Datos del visitante
    nombre_visitante = models.CharField(
        max_length=200,
        verbose_name='Nombre del Visitante'
    )
    empresa = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Empresa'
    )
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefono'
    )
    identificacion_tipo = models.CharField(
        max_length=20,
        choices=IDENTIFICACION_CHOICES,
        default='ine',
        verbose_name='Tipo de Identificacion'
    )
    identificacion_numero = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Numero de Identificacion'
    )
    foto_visitante = models.ImageField(
        storage=MediaStorage(),
        upload_to='visitas/fotos/',
        null=True,
        blank=True,
        verbose_name='Foto del Visitante'
    )

    # Foto de identificacion para verificacion
    foto_identificacion = models.ImageField(
        storage=MediaStorage(),
        upload_to='visitas/identificaciones/',
        null=True,
        blank=True,
        verbose_name='Foto de Identificacion'
    )

    # Detalles de la visita
    motivo = models.TextField(
        verbose_name='Motivo de Visita'
    )
    departamento_destino = models.ForeignKey(
        'organizacion.Departamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visitas',
        verbose_name='Departamento Destino'
    )

    # Programacion
    fecha_programada = models.DateField(
        verbose_name='Fecha Programada'
    )
    hora_programada = models.TimeField(
        verbose_name='Hora Programada'
    )
    duracion_estimada = models.IntegerField(
        default=60,
        verbose_name='Duracion Estimada (minutos)'
    )

    # Control de entrada/salida
    fecha_entrada = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha/Hora de Entrada'
    )
    fecha_salida = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha/Hora de Salida'
    )

    # QR
    codigo_qr = models.ImageField(
        storage=MediaStorage(),
        upload_to='visitas/qr/',
        null=True,
        blank=True,
        verbose_name='Codigo QR'
    )

    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )

    # Autorizacion
    autorizado_por = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visitas_autorizadas',
        verbose_name='Autorizado Por'
    )
    fecha_autorizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Autorizacion'
    )
    comentarios_autorizacion = models.TextField(
        blank=True,
        verbose_name='Comentarios de Autorizacion'
    )

    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Visita'
        verbose_name_plural = 'Visitas'
        ordering = ['-fecha_programada', '-hora_programada']

    def __str__(self):
        return f"{self.nombre_visitante} - {self.fecha_programada} ({self.get_estado_display()})"

    @property
    def codigo_corto(self):
        """Retorna los primeros 8 caracteres del UUID para mostrar"""
        return str(self.codigo_visita)[:8].upper()

    def generar_qr(self):
        """Genera el codigo QR para la visita"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(self.codigo_visita))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"qr_{self.codigo_visita}.png"
        self.codigo_qr.save(filename, ContentFile(buffer.read()), save=False)
        buffer.close()

    def autorizar(self, empleado, comentarios=''):
        """Autoriza la visita"""
        self.estado = 'autorizado'
        self.autorizado_por = empleado
        self.fecha_autorizacion = timezone.now()
        self.comentarios_autorizacion = comentarios
        if not self.codigo_qr:
            self.generar_qr()
        self.save()

    def rechazar(self, empleado, comentarios=''):
        """Rechaza la visita"""
        self.estado = 'rechazado'
        self.autorizado_por = empleado
        self.fecha_autorizacion = timezone.now()
        self.comentarios_autorizacion = comentarios
        self.save()

    def registrar_entrada(self):
        """Registra la entrada del visitante"""
        self.estado = 'en_sitio'
        self.fecha_entrada = timezone.now()
        self.save()

    def registrar_salida(self):
        """Registra la salida del visitante"""
        self.estado = 'finalizado'
        self.fecha_salida = timezone.now()
        self.save()

    def cancelar(self):
        """Cancela la visita"""
        self.estado = 'cancelado'
        self.save()

    def marcar_no_show(self):
        """Marca la visita como no presentada"""
        self.estado = 'no_show'
        self.save()

    def puede_registrar_entrada(self):
        """Verifica si se puede registrar entrada"""
        return self.estado == 'autorizado'

    def puede_registrar_salida(self):
        """Verifica si se puede registrar salida"""
        return self.estado == 'en_sitio'
