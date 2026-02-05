from rest_framework import serializers
from .models import MotivoVisita, Visita
from empleados.serializers import EmpleadoListSerializer
from organizacion.serializers import DepartamentoListSerializer


class MotivoVisitaSerializer(serializers.ModelSerializer):
    """Serializer para motivos de visita"""

    class Meta:
        model = MotivoVisita
        fields = ('id', 'nombre', 'descripcion', 'requiere_autorizacion', 'activo')
        read_only_fields = ('id',)


class VisitaListSerializer(serializers.ModelSerializer):
    """Serializer para lista de visitas"""
    departamento_nombre = serializers.SerializerMethodField()
    codigo_corto = serializers.ReadOnlyField()

    class Meta:
        model = Visita
        fields = (
            'id', 'codigo_visita', 'codigo_corto', 'nombre_visitante', 'empresa',
            'motivo', 'departamento_destino', 'departamento_nombre',
            'fecha_programada', 'hora_programada', 'estado', 'fecha_entrada', 'fecha_salida'
        )

    def get_departamento_nombre(self, obj):
        return obj.departamento_destino.nombre if obj.departamento_destino else None


class VisitaDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para visita"""
    departamento_destino = DepartamentoListSerializer(read_only=True)
    autorizado_por = EmpleadoListSerializer(read_only=True)
    codigo_corto = serializers.ReadOnlyField()
    qr_url = serializers.SerializerMethodField()

    class Meta:
        model = Visita
        fields = (
            'id', 'codigo_visita', 'codigo_corto', 'nombre_visitante', 'empresa',
            'email', 'telefono', 'identificacion_tipo', 'identificacion_numero',
            'foto_visitante', 'foto_identificacion', 'motivo',
            'departamento_destino', 'fecha_programada', 'hora_programada', 'duracion_estimada',
            'fecha_entrada', 'fecha_salida', 'codigo_qr', 'qr_url', 'estado',
            'autorizado_por', 'fecha_autorizacion', 'comentarios_autorizacion',
            'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'codigo_visita', 'fecha_creacion', 'fecha_actualizacion')

    def get_qr_url(self, obj):
        if obj.codigo_qr:
            return obj.codigo_qr.url
        return None


class VisitaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear visita (registro publico)"""

    class Meta:
        model = Visita
        fields = (
            'nombre_visitante', 'empresa', 'email', 'telefono',
            'identificacion_tipo', 'identificacion_numero', 'foto_visitante', 'foto_identificacion',
            'motivo', 'departamento_destino',
            'fecha_programada', 'hora_programada', 'duracion_estimada'
        )

    def create(self, validated_data):
        visita = Visita.objects.create(**validated_data)
        # Autorizar automaticamente
        visita.estado = 'autorizado'
        visita.generar_qr()
        visita.save()
        return visita


class VisitaUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar visita"""

    class Meta:
        model = Visita
        fields = (
            'nombre_visitante', 'empresa', 'email', 'telefono',
            'identificacion_tipo', 'identificacion_numero', 'foto_visitante', 'foto_identificacion',
            'motivo', 'departamento_destino',
            'fecha_programada', 'hora_programada', 'duracion_estimada'
        )

    def validate(self, data):
        if self.instance and self.instance.estado not in ['pendiente', 'autorizado']:
            raise serializers.ValidationError(
                "Solo se pueden modificar visitas pendientes o autorizadas."
            )
        return data


class AutorizarVisitaSerializer(serializers.Serializer):
    """Serializer para autorizar/rechazar visita"""
    comentarios = serializers.CharField(required=False, allow_blank=True, default='')


class VerificarQRSerializer(serializers.Serializer):
    """Serializer para verificar QR"""
    codigo = serializers.CharField()

    def validate_codigo(self, value):
        import uuid
        try:
            uuid.UUID(value)
        except ValueError:
            raise serializers.ValidationError("Codigo de visita invalido.")
        return value


class RegistrarMovimientoSerializer(serializers.Serializer):
    """Serializer para registrar entrada/salida"""
    codigo = serializers.CharField()
    tipo = serializers.ChoiceField(choices=['entrada', 'salida'])
