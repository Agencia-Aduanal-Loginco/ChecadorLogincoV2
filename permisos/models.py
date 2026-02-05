from django.db import models
from django.utils import timezone

from checador.storage_backends import MediaStorage


class TipoPermiso(models.Model):
    """Modelo para tipos de permiso laboral"""

    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Codigo'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripcion'
    )
    requiere_evidencia = models.BooleanField(
        default=False,
        verbose_name='Requiere Evidencia'
    )
    dias_maximos = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Dias Maximos'
    )
    dias_anticipacion = models.IntegerField(
        default=1,
        verbose_name='Dias de Anticipacion Requeridos'
    )
    afecta_salario = models.BooleanField(
        default=True,
        verbose_name='Con Goce de Sueldo'
    )
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        verbose_name='Color (hex)'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tipo de Permiso'
        verbose_name_plural = 'Tipos de Permiso'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class SolicitudPermiso(models.Model):
    """Modelo para solicitudes de permiso laboral"""

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
    ]

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='solicitudes_permiso',
        verbose_name='Empleado'
    )
    tipo_permiso = models.ForeignKey(
        TipoPermiso,
        on_delete=models.PROTECT,
        related_name='solicitudes',
        verbose_name='Tipo de Permiso'
    )
    fecha_inicio = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    fecha_fin = models.DateField(
        verbose_name='Fecha de Fin'
    )
    hora_inicio = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Inicio'
    )
    hora_fin = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Fin'
    )
    motivo = models.TextField(
        verbose_name='Motivo'
    )
    evidencia = models.FileField(
        storage=MediaStorage(),
        upload_to='permisos/evidencias/',
        null=True,
        blank=True,
        verbose_name='Evidencia'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador',
        verbose_name='Estado'
    )
    aprobador = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permisos_aprobados',
        verbose_name='Aprobador'
    )
    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Resolucion'
    )
    comentarios_resolucion = models.TextField(
        blank=True,
        verbose_name='Comentarios de Resolucion'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Solicitud de Permiso'
        verbose_name_plural = 'Solicitudes de Permiso'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.empleado} - {self.tipo_permiso} ({self.fecha_inicio} - {self.fecha_fin})"

    @property
    def dias_solicitados(self):
        """Calcula el numero de dias solicitados"""
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days + 1
        return 0

    @property
    def es_por_horas(self):
        """Indica si el permiso es por horas"""
        return self.hora_inicio is not None and self.hora_fin is not None

    def aprobar(self, aprobador, comentarios=''):
        """Aprueba la solicitud de permiso"""
        self.estado = 'aprobado'
        self.aprobador = aprobador
        self.fecha_resolucion = timezone.now()
        self.comentarios_resolucion = comentarios
        self.save()
        HistorialPermiso.objects.create(
            solicitud=self,
            accion='aprobado',
            usuario=aprobador,
            comentarios=comentarios
        )

    def rechazar(self, aprobador, comentarios=''):
        """Rechaza la solicitud de permiso"""
        self.estado = 'rechazado'
        self.aprobador = aprobador
        self.fecha_resolucion = timezone.now()
        self.comentarios_resolucion = comentarios
        self.save()
        HistorialPermiso.objects.create(
            solicitud=self,
            accion='rechazado',
            usuario=aprobador,
            comentarios=comentarios
        )

    def cancelar(self, usuario, comentarios=''):
        """Cancela la solicitud de permiso"""
        self.estado = 'cancelado'
        self.save()
        HistorialPermiso.objects.create(
            solicitud=self,
            accion='cancelado',
            usuario=usuario,
            comentarios=comentarios
        )

    def enviar(self):
        """Envia la solicitud para aprobacion"""
        self.estado = 'pendiente'
        self.save()
        HistorialPermiso.objects.create(
            solicitud=self,
            accion='enviado',
            usuario=self.empleado,
            comentarios='Solicitud enviada para aprobacion'
        )

    def puede_ser_aprobado_por(self, empleado):
        """Verifica si un empleado puede aprobar esta solicitud"""
        from organizacion.models import RelacionSupervision
        # El empleado no puede aprobar su propia solicitud
        if empleado == self.empleado:
            return False
        # Verificar si es supervisor directo
        relacion = RelacionSupervision.objects.filter(
            supervisor=empleado,
            subordinado=self.empleado,
            puede_autorizar_permisos=True,
            activo=True
        ).first()
        if relacion and relacion.esta_vigente():
            return True
        # Verificar si es responsable del departamento
        if hasattr(self.empleado, 'departamento_obj') and self.empleado.departamento_obj:
            if self.empleado.departamento_obj.responsable == empleado:
                return True
        # Staff puede aprobar cualquier permiso
        if empleado.user.is_staff:
            return True
        return False


class HistorialPermiso(models.Model):
    """Modelo para auditar cambios en solicitudes de permiso"""

    ACCION_CHOICES = [
        ('creado', 'Creado'),
        ('enviado', 'Enviado'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
        ('modificado', 'Modificado'),
    ]

    solicitud = models.ForeignKey(
        SolicitudPermiso,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name='Solicitud'
    )
    accion = models.CharField(
        max_length=20,
        choices=ACCION_CHOICES,
        verbose_name='Accion'
    )
    usuario = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Usuario'
    )
    comentarios = models.TextField(
        blank=True,
        verbose_name='Comentarios'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historial de Permiso'
        verbose_name_plural = 'Historial de Permisos'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.solicitud} - {self.get_accion_display()} ({self.fecha})"
