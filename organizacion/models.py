from django.db import models


class Departamento(models.Model):
    """Modelo para representar un departamento en la estructura organizacional"""

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre'
    )
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Codigo'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripcion'
    )
    departamento_padre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subdepartamentos',
        verbose_name='Departamento Padre'
    )
    responsable = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departamentos_a_cargo',
        verbose_name='Responsable'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def get_nivel(self):
        """Retorna el nivel de jerarquia del departamento"""
        nivel = 0
        dept = self
        while dept.departamento_padre:
            nivel += 1
            dept = dept.departamento_padre
        return nivel

    def get_ruta(self):
        """Retorna la ruta completa desde la raiz hasta este departamento"""
        ruta = [self]
        dept = self
        while dept.departamento_padre:
            ruta.insert(0, dept.departamento_padre)
            dept = dept.departamento_padre
        return ruta

    def get_subordinados_directos(self):
        """Retorna los departamentos que dependen directamente de este"""
        return self.subdepartamentos.filter(activo=True)

    def get_todos_subordinados(self):
        """Retorna todos los departamentos subordinados recursivamente"""
        subordinados = list(self.get_subordinados_directos())
        for sub in self.get_subordinados_directos():
            subordinados.extend(sub.get_todos_subordinados())
        return subordinados


class RelacionSupervision(models.Model):
    """Modelo para definir relaciones de supervision entre empleados"""

    TIPO_RELACION_CHOICES = [
        ('directa', 'Directa'),
        ('funcional', 'Funcional'),
        ('temporal', 'Temporal'),
    ]

    supervisor = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='subordinados_relaciones',
        verbose_name='Supervisor'
    )
    subordinado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='supervisores_relaciones',
        verbose_name='Subordinado'
    )
    tipo_relacion = models.CharField(
        max_length=20,
        choices=TIPO_RELACION_CHOICES,
        default='directa',
        verbose_name='Tipo de Relacion'
    )
    puede_autorizar_permisos = models.BooleanField(
        default=True,
        verbose_name='Puede Autorizar Permisos'
    )
    fecha_inicio = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Relacion de Supervision'
        verbose_name_plural = 'Relaciones de Supervision'
        ordering = ['supervisor', 'subordinado']
        unique_together = ['supervisor', 'subordinado', 'tipo_relacion']

    def __str__(self):
        return f"{self.supervisor} -> {self.subordinado} ({self.get_tipo_relacion_display()})"

    def esta_vigente(self):
        """Verifica si la relacion esta vigente"""
        from django.utils import timezone
        hoy = timezone.now().date()
        if not self.activo:
            return False
        if self.fecha_fin and self.fecha_fin < hoy:
            return False
        return self.fecha_inicio <= hoy
