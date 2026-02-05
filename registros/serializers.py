from rest_framework import serializers
from .models import RegistroAsistencia
from empleados.serializers import EmpleadoListSerializer


class RegistroAsistenciaSerializer(serializers.ModelSerializer):
    """Serializer para registros de asistencia"""
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    empleado_codigo = serializers.CharField(source='empleado.codigo_empleado', read_only=True)
    esta_completo = serializers.ReadOnlyField()
    tiempo_trabajado_str = serializers.ReadOnlyField()
    
    class Meta:
        model = RegistroAsistencia
        fields = '__all__'
        read_only_fields = (
            'id', 'fecha_creacion', 'fecha_actualizacion', 
            'horas_trabajadas', 'retardo', 'incidencia', 'descripcion_incidencia'
        )


class VerificarRostroSerializer(serializers.Serializer):
    """Serializer para verificar rostro sin marcar asistencia"""
    foto = serializers.ImageField(required=True)


class MarcarAsistenciaSerializer(serializers.Serializer):
    """Serializer para marcar asistencia con reconocimiento facial"""
    foto = serializers.ImageField(required=True)
    tipo = serializers.ChoiceField(
        choices=['entrada', 'salida', 'salida_comida', 'entrada_comida'], 
        required=True
    )
    latitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitud = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    ubicacion = serializers.CharField(required=False, allow_blank=True)
