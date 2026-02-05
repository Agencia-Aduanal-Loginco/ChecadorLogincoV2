from rest_framework import serializers
from .models import Departamento, RelacionSupervision
from empleados.serializers import EmpleadoListSerializer


class DepartamentoListSerializer(serializers.ModelSerializer):
    """Serializer para lista de departamentos"""
    responsable_nombre = serializers.SerializerMethodField()
    departamento_padre_nombre = serializers.SerializerMethodField()
    nivel = serializers.SerializerMethodField()

    class Meta:
        model = Departamento
        fields = (
            'id', 'codigo', 'nombre', 'departamento_padre', 'departamento_padre_nombre',
            'responsable', 'responsable_nombre', 'activo', 'nivel'
        )

    def get_responsable_nombre(self, obj):
        return obj.responsable.nombre_completo if obj.responsable else None

    def get_departamento_padre_nombre(self, obj):
        return obj.departamento_padre.nombre if obj.departamento_padre else None

    def get_nivel(self, obj):
        return obj.get_nivel()


class DepartamentoDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para departamento"""
    responsable = EmpleadoListSerializer(read_only=True)
    subdepartamentos = serializers.SerializerMethodField()
    ruta = serializers.SerializerMethodField()

    class Meta:
        model = Departamento
        fields = (
            'id', 'codigo', 'nombre', 'descripcion', 'departamento_padre',
            'responsable', 'activo', 'subdepartamentos', 'ruta',
            'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')

    def get_subdepartamentos(self, obj):
        subdepts = obj.get_subordinados_directos()
        return DepartamentoListSerializer(subdepts, many=True).data

    def get_ruta(self, obj):
        return [{'id': d.id, 'nombre': d.nombre} for d in obj.get_ruta()]


class DepartamentoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar departamento"""

    class Meta:
        model = Departamento
        fields = (
            'codigo', 'nombre', 'descripcion', 'departamento_padre',
            'responsable', 'activo'
        )


class DepartamentoOrganigramaSerializer(serializers.ModelSerializer):
    """Serializer para el organigrama"""
    responsable_nombre = serializers.SerializerMethodField()
    responsable_foto = serializers.SerializerMethodField()
    subdepartamentos = serializers.SerializerMethodField()
    empleados_count = serializers.SerializerMethodField()

    class Meta:
        model = Departamento
        fields = (
            'id', 'codigo', 'nombre', 'responsable', 'responsable_nombre',
            'responsable_foto', 'subdepartamentos', 'empleados_count'
        )

    def get_responsable_nombre(self, obj):
        return obj.responsable.nombre_completo if obj.responsable else None

    def get_responsable_foto(self, obj):
        if obj.responsable and obj.responsable.foto_rostro:
            return obj.responsable.foto_rostro.url
        return None

    def get_subdepartamentos(self, obj):
        subdepts = obj.get_subordinados_directos()
        return DepartamentoOrganigramaSerializer(subdepts, many=True).data

    def get_empleados_count(self, obj):
        from empleados.models import Empleado
        return Empleado.objects.filter(departamento_obj=obj, activo=True).count()


class RelacionSupervisionListSerializer(serializers.ModelSerializer):
    """Serializer para lista de relaciones"""
    supervisor_nombre = serializers.SerializerMethodField()
    subordinado_nombre = serializers.SerializerMethodField()
    vigente = serializers.SerializerMethodField()

    class Meta:
        model = RelacionSupervision
        fields = (
            'id', 'supervisor', 'supervisor_nombre', 'subordinado', 'subordinado_nombre',
            'tipo_relacion', 'puede_autorizar_permisos', 'fecha_inicio', 'fecha_fin',
            'activo', 'vigente'
        )

    def get_supervisor_nombre(self, obj):
        return obj.supervisor.nombre_completo

    def get_subordinado_nombre(self, obj):
        return obj.subordinado.nombre_completo

    def get_vigente(self, obj):
        return obj.esta_vigente()


class RelacionSupervisionDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para relacion"""
    supervisor = EmpleadoListSerializer(read_only=True)
    subordinado = EmpleadoListSerializer(read_only=True)

    class Meta:
        model = RelacionSupervision
        fields = (
            'id', 'supervisor', 'subordinado', 'tipo_relacion',
            'puede_autorizar_permisos', 'fecha_inicio', 'fecha_fin',
            'activo', 'fecha_creacion', 'fecha_actualizacion'
        )
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')


class RelacionSupervisionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar relacion"""

    class Meta:
        model = RelacionSupervision
        fields = (
            'supervisor', 'subordinado', 'tipo_relacion',
            'puede_autorizar_permisos', 'fecha_inicio', 'fecha_fin', 'activo'
        )

    def validate(self, data):
        if data.get('supervisor') == data.get('subordinado'):
            raise serializers.ValidationError(
                "El supervisor y subordinado no pueden ser la misma persona."
            )
        return data
