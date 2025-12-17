from rest_framework import serializers
from .models import Horario
from empleados.serializers import EmpleadoListSerializer


class HorarioSerializer(serializers.ModelSerializer):
    """Serializer para horarios"""
    empleado_detalle = EmpleadoListSerializer(source='empleado', read_only=True)
    dia_semana_nombre = serializers.CharField(source='get_dia_semana_display', read_only=True)
    horas_dia = serializers.ReadOnlyField()
    
    class Meta:
        model = Horario
        fields = (
            'id', 'empleado', 'empleado_detalle', 'dia_semana',
            'dia_semana_nombre', 'hora_entrada', 'hora_salida',
            'tolerancia_minutos', 'activo', 'horas_dia',
            'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')
    
    def validate(self, attrs):
        """Validación personalizada"""
        if 'hora_entrada' in attrs and 'hora_salida' in attrs:
            if attrs['hora_salida'] <= attrs['hora_entrada']:
                raise serializers.ValidationError({
                    'hora_salida': 'La hora de salida debe ser posterior a la hora de entrada.'
                })
        return attrs


class HorarioCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar horarios"""
    
    class Meta:
        model = Horario
        fields = (
            'empleado', 'dia_semana', 'hora_entrada', 'hora_salida',
            'tolerancia_minutos', 'activo'
        )
    
    def validate(self, attrs):
        """Validación personalizada"""
        if 'hora_entrada' in attrs and 'hora_salida' in attrs:
            if attrs['hora_salida'] <= attrs['hora_entrada']:
                raise serializers.ValidationError({
                    'hora_salida': 'La hora de salida debe ser posterior a la hora de entrada.'
                })
        return attrs


class HorarioBulkCreateSerializer(serializers.Serializer):
    """Serializer para crear horarios en lote para un empleado"""
    empleado = serializers.IntegerField()
    horarios = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_horarios(self, value):
        """Validar que cada horario tenga los campos requeridos"""
        required_fields = ['dia_semana', 'hora_entrada', 'hora_salida']
        for horario in value:
            for field in required_fields:
                if field not in horario:
                    raise serializers.ValidationError(
                        f"El campo '{field}' es requerido en cada horario"
                    )
        return value
    
    def create(self, validated_data):
        """Crear múltiples horarios"""
        from empleados.models import Empleado
        
        empleado_id = validated_data['empleado']
        horarios_data = validated_data['horarios']
        
        try:
            empleado = Empleado.objects.get(id=empleado_id)
        except Empleado.DoesNotExist:
            raise serializers.ValidationError({'empleado': 'Empleado no encontrado'})
        
        horarios_creados = []
        for horario_data in horarios_data:
            horario = Horario.objects.create(
                empleado=empleado,
                **horario_data
            )
            horarios_creados.append(horario)
        
        return horarios_creados
