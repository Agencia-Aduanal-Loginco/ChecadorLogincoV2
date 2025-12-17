from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Empleado


class UserNestedSerializer(serializers.ModelSerializer):
    """Serializer anidado para User"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id', 'username')


class EmpleadoListSerializer(serializers.ModelSerializer):
    """Serializer para lista de empleados (menos campos)"""
    user = UserNestedSerializer(read_only=True)
    nombre_completo = serializers.ReadOnlyField()
    tiene_rostro_registrado = serializers.ReadOnlyField()
    
    class Meta:
        model = Empleado
        fields = (
            'id', 'codigo_empleado', 'user', 'nombre_completo',
            'departamento', 'puesto', 'activo', 'tiene_rostro_registrado'
        )


class EmpleadoDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para empleado"""
    user = UserNestedSerializer(read_only=True)
    nombre_completo = serializers.ReadOnlyField()
    tiene_rostro_registrado = serializers.ReadOnlyField()
    
    class Meta:
        model = Empleado
        fields = (
            'id', 'codigo_empleado', 'user', 'nombre_completo',
            'foto_rostro', 'departamento', 'puesto', 'horas_semana',
            'fecha_ingreso', 'activo', 'tiene_rostro_registrado',
            'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')


class EmpleadoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear empleado con usuario"""
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Empleado
        fields = (
            'id', 'codigo_empleado', 'departamento', 'puesto',
            'horas_semana', 'fecha_ingreso', 'activo',
            'username', 'password', 'email', 'first_name', 'last_name'
        )
        read_only_fields = ('id',)
    
    def create(self, validated_data):
        # Extraer datos del usuario
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        # Crear empleado
        empleado = Empleado.objects.create(user=user, **validated_data)
        return empleado


class EmpleadoUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar empleado"""
    email = serializers.EmailField(write_only=True, required=False)
    first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Empleado
        fields = (
            'departamento', 'puesto', 'horas_semana', 'fecha_ingreso',
            'activo', 'email', 'first_name', 'last_name'
        )
    
    def update(self, instance, validated_data):
        # Actualizar datos del usuario si están presentes
        user = instance.user
        if 'email' in validated_data:
            user.email = validated_data.pop('email')
        if 'first_name' in validated_data:
            user.first_name = validated_data.pop('first_name')
        if 'last_name' in validated_data:
            user.last_name = validated_data.pop('last_name')
        user.save()
        
        # Actualizar empleado
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class RegistrarRostroSerializer(serializers.Serializer):
    """Serializer para registrar rostro de empleado"""
    foto_rostro = serializers.ImageField(required=True)
    
    def validate_foto_rostro(self, value):
        """Validar que el archivo sea una imagen"""
        if not value.content_type.startswith('image/'):
            raise serializers.ValidationError("El archivo debe ser una imagen")
        
        # Validar tamaño (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("La imagen no debe superar 5MB")
        
        return value
