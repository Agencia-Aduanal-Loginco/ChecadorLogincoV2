"""
Serializers para la API REST de it_tickets.

Organización:
- EquipoComputoSerializer  -> CRUD de inventario (solo IT)
- TicketListSerializer     -> Vista resumida para listados
- TicketDetalleSerializer  -> Vista completa con historial
- TicketCrearSerializer    -> Creación por el empleado (campos limitados)
- CambioEstadoSerializer   -> Cambio de estado con validación de transición
- HistorialTicketSerializer
- MantenimientoEquipoSerializer
- ImportarCSVSerializer    -> Recibe el archivo CSV para importar inventario
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    EquipoComputo, Ticket, HistorialTicket, MantenimientoEquipo,
    EstadoTicket, TipoEquipo, EstadoEquipo, CategoriaTicket, PrioridadTicket,
    TipoMantenimiento,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class UserResumenSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'nombre_completo', 'email']

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username


# ---------------------------------------------------------------------------
# EquipoComputo
# ---------------------------------------------------------------------------

class EquipoComputoSerializer(serializers.ModelSerializer):
    """Serializer completo para gestión de inventario (solo IT)."""

    empleado_nombre = serializers.SerializerMethodField(read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    requiere_mantenimiento_pronto = serializers.BooleanField(read_only=True)
    mantenimiento_vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = EquipoComputo
        fields = [
            'id', 'empleado', 'empleado_nombre', 'usuario_nombre',
            'tipo', 'tipo_display', 'numero_serie', 'marca', 'modelo',
            'tiene_monitor', 'marca_monitor',
            'telefono_serie', 'mac_telefono',
            'estado', 'estado_display',
            'fecha_ultimo_mantenimiento', 'fecha_proximo_mantenimiento',
            'requiere_mantenimiento_pronto', 'mantenimiento_vencido',
            'notas',
            'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = [
            'fecha_creacion', 'fecha_actualizacion',
            'empleado_nombre', 'tipo_display', 'estado_display',
            'requiere_mantenimiento_pronto', 'mantenimiento_vencido',
        ]

    def get_empleado_nombre(self, obj):
        if obj.empleado:
            return obj.empleado.nombre_completo
        return None

    def validate_numero_serie(self, value):
        """Número de serie no puede estar vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "El número de serie es obligatorio."
            )
        return value.strip().upper()


class EquipoComputoResumenSerializer(serializers.ModelSerializer):
    """Versión ligera para listados y selects."""

    class Meta:
        model = EquipoComputo
        fields = ['id', 'usuario_nombre', 'tipo', 'numero_serie', 'marca', 'modelo', 'estado']


# ---------------------------------------------------------------------------
# HistorialTicket
# ---------------------------------------------------------------------------

class HistorialTicketSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    estado_anterior_display = serializers.CharField(
        source='get_estado_anterior_display', read_only=True
    )
    estado_nuevo_display = serializers.CharField(
        source='get_estado_nuevo_display', read_only=True
    )

    class Meta:
        model = HistorialTicket
        fields = [
            'id', 'estado_anterior', 'estado_anterior_display',
            'estado_nuevo', 'estado_nuevo_display',
            'usuario', 'usuario_nombre', 'comentario', 'fecha',
        ]

    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.username
        return 'Sistema'


# ---------------------------------------------------------------------------
# Ticket - Crear (empleado)
# ---------------------------------------------------------------------------

class TicketCrearSerializer(serializers.ModelSerializer):
    """
    Serializer para que un empleado cree un ticket.
    El empleado no puede asignar prioridad ni estado: eso es responsabilidad de IT.
    """

    class Meta:
        model = Ticket
        fields = [
            'titulo', 'descripcion', 'categoria', 'equipo',
        ]

    def validate_titulo(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "El título debe tener al menos 5 caracteres."
            )
        return value.strip()

    def validate_descripcion(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "La descripción debe tener al menos 10 caracteres."
            )
        return value.strip()

    def create(self, validated_data):
        """
        El empleado se toma del contexto de la petición (request.user.empleado).
        Si el usuario no tiene empleado asociado, se lanza error de validación.
        """
        request = self.context.get('request')
        try:
            empleado = request.user.empleado
        except AttributeError:
            raise serializers.ValidationError(
                "Tu usuario no tiene un perfil de empleado asociado."
            )
        validated_data['empleado'] = empleado
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Ticket - Lista (resumen)
# ---------------------------------------------------------------------------

class TicketListSerializer(serializers.ModelSerializer):
    """Vista resumida para listados con paginación."""

    empleado_nombre = serializers.SerializerMethodField()
    asignado_a_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    equipo_resumen = serializers.SerializerMethodField()
    tiempo_resolucion_horas = serializers.FloatField(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'folio', 'titulo',
            'categoria', 'categoria_display',
            'prioridad', 'prioridad_display',
            'estado', 'estado_display',
            'empleado', 'empleado_nombre',
            'asignado_a', 'asignado_a_nombre',
            'equipo', 'equipo_resumen',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_resolucion',
            'tiempo_resolucion_horas',
        ]

    def get_empleado_nombre(self, obj):
        return obj.empleado.nombre_completo

    def get_asignado_a_nombre(self, obj):
        if obj.asignado_a:
            return obj.asignado_a.get_full_name() or obj.asignado_a.username
        return None

    def get_equipo_resumen(self, obj):
        if obj.equipo:
            return f"{obj.equipo.marca} {obj.equipo.modelo} [{obj.equipo.numero_serie}]"
        return None


# ---------------------------------------------------------------------------
# Ticket - Detalle completo (IT y empleado propietario)
# ---------------------------------------------------------------------------

class TicketDetalleSerializer(serializers.ModelSerializer):
    """Vista completa incluyendo historial de cambios."""

    empleado_nombre = serializers.SerializerMethodField()
    asignado_a_detalle = UserResumenSerializer(source='asignado_a', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    equipo_detalle = EquipoComputoResumenSerializer(source='equipo', read_only=True)
    historial = HistorialTicketSerializer(many=True, read_only=True)
    tiempo_resolucion_horas = serializers.FloatField(read_only=True)
    esta_abierto = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'folio', 'titulo', 'descripcion',
            'categoria', 'categoria_display',
            'prioridad', 'prioridad_display',
            'estado', 'estado_display', 'esta_abierto',
            'motivo_espera', 'solucion',
            'empleado', 'empleado_nombre',
            'asignado_a', 'asignado_a_detalle',
            'equipo', 'equipo_detalle',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_resolucion',
            'tiempo_resolucion_horas',
            'historial',
        ]


# ---------------------------------------------------------------------------
# Ticket - Actualización por IT
# ---------------------------------------------------------------------------

class TicketActualizarITSerializer(serializers.ModelSerializer):
    """
    Serializer para que IT actualice campos de gestión del ticket.
    IT puede asignar prioridad, responsable y escribir la solución.
    El cambio de estado se hace con un endpoint dedicado.
    """

    class Meta:
        model = Ticket
        fields = ['prioridad', 'asignado_a', 'solucion', 'equipo']


# ---------------------------------------------------------------------------
# CambioEstado
# ---------------------------------------------------------------------------

class CambioEstadoSerializer(serializers.Serializer):
    """
    Serializer para el endpoint de cambio de estado.
    Valida que la transición sea permitida antes de aplicarla.
    """

    nuevo_estado = serializers.ChoiceField(choices=EstadoTicket.choices)
    comentario = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=1000
    )
    motivo_espera = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=500
    )
    solucion = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )

    def validate(self, data):
        ticket = self.context.get('ticket')
        nuevo_estado = data.get('nuevo_estado')

        if not ticket.puede_cambiar_a(nuevo_estado):
            raise serializers.ValidationError({
                'nuevo_estado': (
                    f"Transición no permitida: "
                    f"'{ticket.get_estado_display()}' -> "
                    f"'{EstadoTicket(nuevo_estado).label}'"
                )
            })

        if nuevo_estado == EstadoTicket.ESPERA:
            motivo = data.get('motivo_espera', '').strip()
            if not motivo and not ticket.motivo_espera:
                raise serializers.ValidationError({
                    'motivo_espera': (
                        "Debe especificar el motivo de espera cuando "
                        "se pone el ticket en este estado."
                    )
                })

        return data


# ---------------------------------------------------------------------------
# MantenimientoEquipo
# ---------------------------------------------------------------------------

class MantenimientoEquipoSerializer(serializers.ModelSerializer):
    equipo_resumen = EquipoComputoResumenSerializer(source='equipo', read_only=True)
    tipo_display = serializers.CharField(
        source='get_tipo_mantenimiento_display', read_only=True
    )
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MantenimientoEquipo
        fields = [
            'id', 'equipo', 'equipo_resumen',
            'tipo_mantenimiento', 'tipo_display',
            'descripcion', 'fecha_realizado', 'fecha_proximo',
            'tecnico', 'costo', 'observaciones',
            'registrado_por', 'registrado_por_nombre',
            'fecha_creacion',
        ]
        read_only_fields = ['fecha_creacion', 'registrado_por', 'registrado_por_nombre']

    def get_registrado_por_nombre(self, obj):
        if obj.registrado_por:
            return obj.registrado_por.get_full_name() or obj.registrado_por.username
        return None

    def validate(self, data):
        fecha_realizado = data.get('fecha_realizado')
        fecha_proximo = data.get('fecha_proximo')
        if fecha_proximo and fecha_realizado and fecha_proximo <= fecha_realizado:
            raise serializers.ValidationError({
                'fecha_proximo': (
                    "La fecha del próximo mantenimiento debe ser "
                    "posterior a la fecha en que se realizó."
                )
            })
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['registrado_por'] = request.user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Importar CSV
# ---------------------------------------------------------------------------

class ImportarCSVSerializer(serializers.Serializer):
    """Recibe el archivo CSV del inventario para procesarlo."""

    archivo = serializers.FileField(
        help_text="Archivo CSV con columnas: "
                  "Codigo Empleado, Usuario, Tipo, Numero Serie, Marca, Modelo, "
                  "R, U, Monitores, Marca, TELEFONO, TEF MAC"
    )
    actualizar_existentes = serializers.BooleanField(
        default=False,
        help_text=(
            "Si es True, actualiza los registros existentes por número de serie. "
            "Si es False (default), omite duplicados."
        )
    )

    def validate_archivo(self, value):
        nombre = value.name.lower()
        if not nombre.endswith('.csv'):
            raise serializers.ValidationError(
                "Solo se aceptan archivos con extensión .csv"
            )
        # Límite de 5MB
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "El archivo no debe superar los 5 MB."
            )
        return value
