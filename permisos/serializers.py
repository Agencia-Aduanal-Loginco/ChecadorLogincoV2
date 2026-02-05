from rest_framework import serializers
from .models import TipoPermiso, SolicitudPermiso, HistorialPermiso
from empleados.serializers import EmpleadoListSerializer


class TipoPermisoSerializer(serializers.ModelSerializer):
    """Serializer para tipos de permiso"""

    class Meta:
        model = TipoPermiso
        fields = (
            'id', 'codigo', 'nombre', 'descripcion', 'requiere_evidencia',
            'dias_maximos', 'dias_anticipacion', 'afecta_salario', 'color', 'activo'
        )
        read_only_fields = ('id',)


class HistorialPermisoSerializer(serializers.ModelSerializer):
    """Serializer para historial de permiso"""
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = HistorialPermiso
        fields = ('id', 'accion', 'usuario', 'usuario_nombre', 'comentarios', 'fecha')

    def get_usuario_nombre(self, obj):
        return obj.usuario.nombre_completo if obj.usuario else None


class SolicitudPermisoListSerializer(serializers.ModelSerializer):
    """Serializer para lista de solicitudes"""
    empleado_nombre = serializers.SerializerMethodField()
    tipo_permiso_nombre = serializers.SerializerMethodField()
    tipo_permiso_color = serializers.SerializerMethodField()
    dias_solicitados = serializers.ReadOnlyField()
    es_por_horas = serializers.ReadOnlyField()

    class Meta:
        model = SolicitudPermiso
        fields = (
            'id', 'empleado', 'empleado_nombre', 'tipo_permiso', 'tipo_permiso_nombre',
            'tipo_permiso_color', 'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin',
            'estado', 'dias_solicitados', 'es_por_horas', 'fecha_creacion'
        )

    def get_empleado_nombre(self, obj):
        return obj.empleado.nombre_completo

    def get_tipo_permiso_nombre(self, obj):
        return obj.tipo_permiso.nombre

    def get_tipo_permiso_color(self, obj):
        return obj.tipo_permiso.color


class SolicitudPermisoDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para solicitud"""
    empleado = EmpleadoListSerializer(read_only=True)
    tipo_permiso = TipoPermisoSerializer(read_only=True)
    aprobador = EmpleadoListSerializer(read_only=True)
    historial = HistorialPermisoSerializer(many=True, read_only=True)
    dias_solicitados = serializers.ReadOnlyField()
    es_por_horas = serializers.ReadOnlyField()

    class Meta:
        model = SolicitudPermiso
        fields = (
            'id', 'empleado', 'tipo_permiso', 'fecha_inicio', 'fecha_fin',
            'hora_inicio', 'hora_fin', 'motivo', 'evidencia', 'estado',
            'aprobador', 'fecha_resolucion', 'comentarios_resolucion',
            'dias_solicitados', 'es_por_horas', 'historial',
            'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')


class SolicitudPermisoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear solicitud"""

    class Meta:
        model = SolicitudPermiso
        fields = (
            'tipo_permiso', 'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin',
            'motivo', 'evidencia'
        )

    def validate(self, data):
        if data['fecha_fin'] < data['fecha_inicio']:
            raise serializers.ValidationError(
                "La fecha de fin no puede ser anterior a la fecha de inicio."
            )

        tipo_permiso = data['tipo_permiso']
        dias = (data['fecha_fin'] - data['fecha_inicio']).days + 1

        if tipo_permiso.dias_maximos and dias > tipo_permiso.dias_maximos:
            raise serializers.ValidationError(
                f"El tipo de permiso '{tipo_permiso.nombre}' permite maximo {tipo_permiso.dias_maximos} dias."
            )

        if tipo_permiso.requiere_evidencia and not data.get('evidencia'):
            raise serializers.ValidationError(
                f"El tipo de permiso '{tipo_permiso.nombre}' requiere evidencia."
            )

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'empleado'):
            validated_data['empleado'] = request.user.empleado
        solicitud = SolicitudPermiso.objects.create(**validated_data)
        HistorialPermiso.objects.create(
            solicitud=solicitud,
            accion='creado',
            usuario=solicitud.empleado,
            comentarios='Solicitud creada'
        )
        return solicitud


class SolicitudPermisoUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar solicitud (solo borrador)"""

    class Meta:
        model = SolicitudPermiso
        fields = (
            'tipo_permiso', 'fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin',
            'motivo', 'evidencia'
        )

    def validate(self, data):
        instance = self.instance
        if instance and instance.estado != 'borrador':
            raise serializers.ValidationError(
                "Solo se pueden modificar solicitudes en estado borrador."
            )
        return data


class AprobarRechazarSerializer(serializers.Serializer):
    """Serializer para aprobar/rechazar solicitud"""
    comentarios = serializers.CharField(required=False, allow_blank=True, default='')
