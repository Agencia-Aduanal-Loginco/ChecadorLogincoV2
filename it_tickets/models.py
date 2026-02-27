"""
Modelos para la app it_tickets.

Gestiona el inventario de equipo de computo y los tickets de soporte IT
para Loginco. Incluye auditoría de cambios de estado y registro de
mantenimientos preventivos y correctivos.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes de estado compartidas
# ---------------------------------------------------------------------------

class EstadoEquipo(models.TextChoices):
    ACTIVO       = 'activo',       'Activo'
    MANTENIMIENTO = 'mantenimiento', 'En Mantenimiento'
    BAJA         = 'baja',         'De Baja'


class TipoEquipo(models.TextChoices):
    DESKTOP  = 'desktop',  'Desktop'
    LAPTOP   = 'laptop',   'Laptop'
    SERVIDOR = 'servidor', 'Servidor'
    IMPRESORA = 'impresora', 'Impresora'
    TABLET   = 'tablet',   'Tablet'
    OTRO     = 'otro',     'Otro'


class CategoriaTicket(models.TextChoices):
    HARDWARE = 'hardware', 'Hardware'
    SOFTWARE = 'software', 'Software'
    RED      = 'red',      'Red / Conectividad'
    OTRO     = 'otro',     'Otro'


class PrioridadTicket(models.TextChoices):
    CRITICA = 'critica', 'Critica'
    ALTA    = 'alta',    'Alta'
    MEDIA   = 'media',   'Media'
    BAJA    = 'baja',    'Baja'


class EstadoTicket(models.TextChoices):
    CREADO   = 'creado',   'Creado'
    PENDIENTE = 'pendiente', 'Pendiente'
    PROCESO  = 'proceso',  'En Proceso'
    ESPERA   = 'espera',   'En Espera'
    CONCLUIDO = 'concluido', 'Concluido'


class TipoMantenimiento(models.TextChoices):
    PREVENTIVO  = 'preventivo',  'Preventivo'
    CORRECTIVO  = 'correctivo',  'Correctivo'


# ---------------------------------------------------------------------------
# Modelo: EquipoComputo
# ---------------------------------------------------------------------------

class EquipoComputo(models.Model):
    """
    Inventario de equipos de computo de la empresa.

    Importado desde el CSV Invetario_Loginco_equipo.csv.
    El campo codigo_empleado es nullable porque algunos equipos no están
    asignados a un empleado específico (por ejemplo, equipos compartidos o
    de auxiliares sin código en el CSV).
    """

    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipos_asignados',
        verbose_name='Empleado Asignado'
    )
    # Guardamos el nombre de usuario tal como viene del CSV/inventario,
    # independientemente de si existe o no un empleado vinculado.
    usuario_nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre de Usuario / Descripción',
        help_text='Nombre del usuario o descripción (ej: Tramitadores, Auxiliar)'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoEquipo.choices,
        default=TipoEquipo.DESKTOP,
        verbose_name='Tipo de Equipo'
    )
    numero_serie = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Número de Serie'
    )
    marca = models.CharField(
        max_length=100,
        verbose_name='Marca'
    )
    modelo = models.CharField(
        max_length=100,
        verbose_name='Modelo'
    )
    tiene_monitor = models.BooleanField(
        default=False,
        verbose_name='Tiene Monitor'
    )
    marca_monitor = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Marca del Monitor'
    )
    # Número de serie del teléfono/extensión (columna TELEFONO del CSV)
    telefono_serie = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Serie del Teléfono'
    )
    # MAC del teléfono IP (columna TEF MAC del CSV)
    mac_telefono = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='MAC del Teléfono'
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoEquipo.choices,
        default=EstadoEquipo.ACTIVO,
        verbose_name='Estado'
    )
    fecha_ultimo_mantenimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Último Mantenimiento'
    )
    fecha_proximo_mantenimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Próximo Mantenimiento',
        db_index=True  # consultado frecuentemente en el scheduler de alertas
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Equipo de Cómputo'
        verbose_name_plural = 'Equipos de Cómputo'
        ordering = ['marca', 'modelo', 'numero_serie']
        indexes = [
            models.Index(fields=['estado'], name='idx_equipo_estado'),
            models.Index(fields=['empleado', 'estado'], name='idx_equipo_empleado_estado'),
        ]

    def __str__(self):
        asignado = self.usuario_nombre or (self.empleado.nombre_completo if self.empleado else 'Sin asignar')
        return f"{self.marca} {self.modelo} [{self.numero_serie}] - {asignado}"

    @property
    def requiere_mantenimiento_pronto(self):
        """Verdadero si el mantenimiento está en los próximos 7 días o ya venció."""
        if not self.fecha_proximo_mantenimiento:
            return False
        return self.fecha_proximo_mantenimiento <= (timezone.now().date() + timezone.timedelta(days=7))

    @property
    def mantenimiento_vencido(self):
        """Verdadero si la fecha de próximo mantenimiento ya pasó."""
        if not self.fecha_proximo_mantenimiento:
            return False
        return self.fecha_proximo_mantenimiento < timezone.now().date()


# ---------------------------------------------------------------------------
# Modelo: Ticket
# ---------------------------------------------------------------------------

class Ticket(models.Model):
    """
    Ticket de soporte IT levantado por un empleado.

    Ciclo de vida: creado -> pendiente -> proceso -> espera -> concluido
    El folio se genera automáticamente en el método save() con el
    patrón TKT-YYYYMMDD-XXX (consistente con el patrón del proyecto).
    """

    folio = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='Folio'
    )
    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name='Empleado que Reporta'
    )
    equipo = models.ForeignKey(
        EquipoComputo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        verbose_name='Equipo Relacionado'
    )
    titulo = models.CharField(
        max_length=200,
        verbose_name='Título'
    )
    descripcion = models.TextField(
        verbose_name='Descripción del Problema'
    )
    categoria = models.CharField(
        max_length=20,
        choices=CategoriaTicket.choices,
        default=CategoriaTicket.OTRO,
        verbose_name='Categoría',
        db_index=True
    )
    # La prioridad es asignada por el equipo de IT, no por el empleado.
    # Valor inicial null hasta que IT la evalúe.
    prioridad = models.CharField(
        max_length=10,
        choices=PrioridadTicket.choices,
        null=True,
        blank=True,
        verbose_name='Prioridad',
        db_index=True
    )
    estado = models.CharField(
        max_length=15,
        choices=EstadoTicket.choices,
        default=EstadoTicket.CREADO,
        verbose_name='Estado',
        db_index=True
    )
    # Solo obligatorio cuando el estado pasa a "espera"
    motivo_espera = models.TextField(
        blank=True,
        verbose_name='Motivo de Espera',
        help_text='Especificar qué se espera: piezas, proveedor, equipo de reemplazo, etc.'
    )
    solucion = models.TextField(
        blank=True,
        verbose_name='Descripción de la Solución'
    )
    # IT asigna el ticket a un usuario del grupo IT
    asignado_a = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_asignados',
        verbose_name='Asignado a (IT)',
        limit_choices_to={'groups__name': 'IT'}
    )
    # Fechas de ciclo de vida
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Resolución'
    )

    class Meta:
        verbose_name = 'Ticket de Soporte IT'
        verbose_name_plural = 'Tickets de Soporte IT'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', 'prioridad'], name='idx_ticket_estado_prioridad'),
            models.Index(fields=['empleado', 'estado'], name='idx_ticket_empleado_estado'),
            models.Index(fields=['fecha_creacion'], name='idx_ticket_fecha_creacion'),
        ]

    def __str__(self):
        return f"{self.folio} - {self.titulo} [{self.get_estado_display()}]"

    def save(self, *args, **kwargs):
        """Genera el folio automáticamente en la primera creación."""
        if not self.folio:
            self.folio = self._generar_folio()
        super().save(*args, **kwargs)

    def _generar_folio(self):
        """
        Genera folio con patrón TKT-YYYYMMDD-XXX.
        Usa select_for_update en un contexto transaccional para evitar
        colisiones en ambientes con múltiples workers.
        """
        from django.db import transaction
        hoy = timezone.now().date()
        prefijo = f"TKT-{hoy.strftime('%Y%m%d')}"
        with transaction.atomic():
            ultimo = (
                Ticket.objects
                .filter(folio__startswith=prefijo)
                .select_for_update()
                .order_by('-folio')
                .first()
            )
            if ultimo:
                try:
                    ultimo_consecutivo = int(ultimo.folio.split('-')[-1])
                except (ValueError, IndexError):
                    ultimo_consecutivo = 0
                consecutivo = ultimo_consecutivo + 1
            else:
                consecutivo = 1
        return f"{prefijo}-{consecutivo:03d}"

    @property
    def tiempo_resolucion_horas(self):
        """Horas transcurridas desde la creación hasta la resolución (o ahora)."""
        fin = self.fecha_resolucion or timezone.now()
        delta = fin - self.fecha_creacion
        return round(delta.total_seconds() / 3600, 1)

    @property
    def esta_abierto(self):
        return self.estado not in (EstadoTicket.CONCLUIDO,)

    def puede_cambiar_a(self, nuevo_estado):
        """
        Valida transiciones de estado permitidas.

        Transiciones válidas:
          creado    -> pendiente
          pendiente -> proceso
          proceso   -> espera, concluido
          espera    -> proceso, concluido
        """
        transiciones = {
            EstadoTicket.CREADO:    [EstadoTicket.PENDIENTE],
            EstadoTicket.PENDIENTE: [EstadoTicket.PROCESO],
            EstadoTicket.PROCESO:   [EstadoTicket.ESPERA, EstadoTicket.CONCLUIDO],
            EstadoTicket.ESPERA:    [EstadoTicket.PROCESO, EstadoTicket.CONCLUIDO],
            EstadoTicket.CONCLUIDO: [],
        }
        return nuevo_estado in transiciones.get(self.estado, [])

    def cambiar_estado(self, nuevo_estado, usuario, comentario='', motivo_espera=''):
        """
        Cambia el estado del ticket validando la transición y registrando el historial.
        Lanza ValueError si la transición no está permitida.
        """
        if not self.puede_cambiar_a(nuevo_estado):
            raise ValueError(
                f"No se puede pasar de '{self.get_estado_display()}' "
                f"a '{EstadoTicket(nuevo_estado).label}'"
            )

        estado_anterior = self.estado
        self.estado = nuevo_estado

        if nuevo_estado == EstadoTicket.ESPERA:
            if not motivo_espera and not self.motivo_espera:
                raise ValueError("Debe especificar el motivo de espera.")
            if motivo_espera:
                self.motivo_espera = motivo_espera

        if nuevo_estado == EstadoTicket.CONCLUIDO:
            self.fecha_resolucion = timezone.now()

        self.save()

        HistorialTicket.objects.create(
            ticket=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            comentario=comentario
        )

        return estado_anterior


# ---------------------------------------------------------------------------
# Modelo: HistorialTicket
# ---------------------------------------------------------------------------

class HistorialTicket(models.Model):
    """
    Registro de auditoría de cada cambio de estado en un Ticket.
    Se crea automáticamente mediante la señal post_save del Ticket
    para capturas de transición, y también explícitamente mediante
    Ticket.cambiar_estado().
    """

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name='Ticket'
    )
    estado_anterior = models.CharField(
        max_length=15,
        choices=EstadoTicket.choices,
        verbose_name='Estado Anterior'
    )
    estado_nuevo = models.CharField(
        max_length=15,
        choices=EstadoTicket.choices,
        verbose_name='Estado Nuevo'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Usuario que Cambió el Estado'
    )
    comentario = models.TextField(
        blank=True,
        verbose_name='Comentario'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historial de Ticket'
        verbose_name_plural = 'Historial de Tickets'
        ordering = ['-fecha']

    def __str__(self):
        return (
            f"{self.ticket.folio}: "
            f"{self.get_estado_anterior_display()} -> {self.get_estado_nuevo_display()} "
            f"({self.fecha.strftime('%d/%m/%Y %H:%M')})"
        )


# ---------------------------------------------------------------------------
# Modelo: MantenimientoEquipo
# ---------------------------------------------------------------------------

class MantenimientoEquipo(models.Model):
    """
    Registro de mantenimientos realizados a un equipo de cómputo.

    Al guardar, actualiza automáticamente los campos
    fecha_ultimo_mantenimiento y fecha_proximo_mantenimiento del equipo
    relacionado, manteniéndolos sincronizados.
    """

    equipo = models.ForeignKey(
        EquipoComputo,
        on_delete=models.CASCADE,
        related_name='mantenimientos',
        verbose_name='Equipo'
    )
    tipo_mantenimiento = models.CharField(
        max_length=15,
        choices=TipoMantenimiento.choices,
        default=TipoMantenimiento.PREVENTIVO,
        verbose_name='Tipo de Mantenimiento'
    )
    descripcion = models.TextField(
        verbose_name='Descripción del Mantenimiento'
    )
    fecha_realizado = models.DateField(
        verbose_name='Fecha Realizado'
    )
    fecha_proximo = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha del Próximo Mantenimiento'
    )
    tecnico = models.CharField(
        max_length=150,
        verbose_name='Técnico Responsable'
    )
    costo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Costo (MXN)'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Registrado Por'
    )

    class Meta:
        verbose_name = 'Mantenimiento de Equipo'
        verbose_name_plural = 'Mantenimientos de Equipo'
        ordering = ['-fecha_realizado']

    def __str__(self):
        return (
            f"{self.get_tipo_mantenimiento_display()} - "
            f"{self.equipo} ({self.fecha_realizado})"
        )

    def save(self, *args, **kwargs):
        """
        Al guardar un mantenimiento, sincroniza las fechas en el equipo.
        Solo actualiza si la fecha_realizado es más reciente que el
        ultimo mantenimiento registrado en el equipo.
        """
        super().save(*args, **kwargs)
        equipo = self.equipo
        # Actualizar último mantenimiento si corresponde
        if (
            not equipo.fecha_ultimo_mantenimiento
            or self.fecha_realizado >= equipo.fecha_ultimo_mantenimiento
        ):
            equipo.fecha_ultimo_mantenimiento = self.fecha_realizado
            if self.fecha_proximo:
                equipo.fecha_proximo_mantenimiento = self.fecha_proximo
            # Si el equipo estaba en mantenimiento, regresarlo a activo
            if equipo.estado == EstadoEquipo.MANTENIMIENTO:
                equipo.estado = EstadoEquipo.ACTIVO
            equipo.save(update_fields=[
                'fecha_ultimo_mantenimiento',
                'fecha_proximo_mantenimiento',
                'estado',
            ])


# ---------------------------------------------------------------------------
# Señales
# ---------------------------------------------------------------------------

@receiver(pre_save, sender=Ticket)
def capturar_estado_anterior(sender, instance, **kwargs):
    """
    Almacena en el objeto el estado anterior antes de guardarlo,
    para que la señal post_save pueda comparar y disparar notificaciones.
    """
    if instance.pk:
        try:
            instance._estado_anterior = Ticket.objects.get(pk=instance.pk).estado
        except Ticket.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Ticket)
def manejar_cambio_estado_ticket(sender, instance, created, **kwargs):
    """
    Después de guardar un ticket:
    - Si es nuevo: notifica al grupo IT.
    - Si cambió a 'espera': notifica al empleado.
    - Si cambió a 'concluido': notifica al empleado.

    Las notificaciones se envían en segundo plano para no bloquear
    la petición HTTP. Si falla el envío de email, se registra en el log
    pero no se propaga la excepción.
    """
    from it_tickets.services.notificaciones import (
        notificar_nuevo_ticket,
        notificar_ticket_en_espera,
        notificar_ticket_concluido,
    )

    estado_anterior = getattr(instance, '_estado_anterior', None)

    if created:
        try:
            notificar_nuevo_ticket(instance)
        except Exception as e:
            logger.error(f"Error notificando nuevo ticket {instance.folio}: {e}")
        return

    # Solo actuar si el estado cambió
    if estado_anterior == instance.estado:
        return

    if instance.estado == EstadoTicket.ESPERA:
        try:
            notificar_ticket_en_espera(instance)
        except Exception as e:
            logger.error(f"Error notificando ticket en espera {instance.folio}: {e}")

    elif instance.estado == EstadoTicket.CONCLUIDO:
        try:
            notificar_ticket_concluido(instance)
        except Exception as e:
            logger.error(f"Error notificando ticket concluido {instance.folio}: {e}")
