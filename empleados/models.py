from django.db import models
from django.contrib.auth.models import User
import pickle
import numpy as np

from checador.storage_backends import MediaStorage

class Empleado(models.Model):
    """Modelo para representar a un empleado del sistema"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='empleado',
        verbose_name='Usuario'
    )
    codigo_empleado = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código de Empleado'
    )
    foto_rostro = models.ImageField(
        storage=MediaStorage(),
        upload_to='rostros/',
        null=True,
        blank=True,
        verbose_name='Foto de Rostro'
    )
    embedding_rostro = models.BinaryField(
        null=True,
        blank=True,
        verbose_name='Encoding Facial'
    )  # Para almacenar el encoding facial

    # Información laboral
    horas_semana = models.IntegerField(
        default=40,
        verbose_name='Horas por Semana'
    )
    departamento = models.CharField(
        max_length=100,
        verbose_name='Departamento'
    )
    departamento_obj = models.ForeignKey(
        'organizacion.Departamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empleados',
        verbose_name='Departamento (Estructura)'
    )
    supervisor_directo = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinados',
        verbose_name='Supervisor Directo'
    )
    puesto = models.CharField(
        max_length=100,
        verbose_name='Puesto',
        blank=True
    )
    fecha_ingreso = models.DateField(
        verbose_name='Fecha de Ingreso',
        null=True,
        blank=True
    )

    # Horario predeterminado
    horario_predeterminado = models.ForeignKey(
        'horarios.TipoHorario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empleados_predeterminados',
        verbose_name='Horario Predeterminado'
    )

    # Estatus
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )

    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['codigo_empleado']

    def __str__(self):
        return f"{self.codigo_empleado} - {self.user.get_full_name() or self.user.username}"

    def set_face_encoding(self, encoding_array):
        """Guarda el encoding facial como bytes"""
        if encoding_array is not None:
            self.embedding_rostro = pickle.dumps(encoding_array)

    def get_face_encoding(self):
        """Recupera el encoding facial como numpy array"""
        if self.embedding_rostro:
            return pickle.loads(self.embedding_rostro)
        return None

    @property
    def nombre_completo(self):
        """Retorna el nombre completo del empleado"""
        return self.user.get_full_name() or self.user.username

    @property
    def tiene_rostro_registrado(self):
        """Verifica si el empleado tiene un rostro registrado"""
        return bool(self.embedding_rostro)
    
    def eliminar_rostro(self):
        """Elimina el registro facial del empleado"""
        self.embedding_rostro = None
        if self.foto_rostro:
            # Eliminar el archivo físico de la foto
            self.foto_rostro.delete(save=False)
            self.foto_rostro = None
        self.save()

    def get_supervisores(self):
        """Retorna lista de supervisores que pueden aprobar permisos"""
        from organizacion.models import RelacionSupervision
        supervisores = []

        # Supervisor directo
        if self.supervisor_directo:
            supervisores.append(self.supervisor_directo)

        # Supervisores de relaciones de supervision
        relaciones = RelacionSupervision.objects.filter(
            subordinado=self,
            puede_autorizar_permisos=True,
            activo=True
        ).select_related('supervisor')

        for relacion in relaciones:
            if relacion.esta_vigente() and relacion.supervisor not in supervisores:
                supervisores.append(relacion.supervisor)

        # Responsable del departamento
        if self.departamento_obj and self.departamento_obj.responsable:
            if self.departamento_obj.responsable not in supervisores:
                supervisores.append(self.departamento_obj.responsable)

        return supervisores
