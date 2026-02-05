from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Horario, TipoHorario, AsignacionHorario
from .serializers import (
    HorarioSerializer,
    HorarioCreateUpdateSerializer,
    HorarioBulkCreateSerializer,
    TipoHorarioSerializer,
    AsignacionHorarioSerializer,
    AsignacionBulkSerializer,
)


class HorarioViewSet(viewsets.ModelViewSet):
    """ViewSet para CRUD de horarios"""
    queryset = Horario.objects.all().select_related('empleado', 'empleado__user')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return HorarioCreateUpdateSerializer
        elif self.action == 'bulk_create':
            return HorarioBulkCreateSerializer
        return HorarioSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        empleado_id = self.request.query_params.get('empleado', None)
        if empleado_id:
            queryset = queryset.filter(empleado_id=empleado_id)

        dia_semana = self.request.query_params.get('dia_semana', None)
        if dia_semana:
            queryset = queryset.filter(dia_semana=dia_semana)

        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)

        return queryset

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Crear multiples horarios para un empleado"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        horarios = serializer.save()

        return Response(
            HorarioSerializer(horarios, many=True).data,
            status=status.HTTP_201_CREATED
        )


class TipoHorarioViewSet(viewsets.ModelViewSet):
    """ViewSet para CRUD de tipos de horario"""
    queryset = TipoHorario.objects.all()
    serializer_class = TipoHorarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)
        return queryset


class AsignacionHorarioViewSet(viewsets.ModelViewSet):
    """ViewSet para asignaciones de horario"""
    queryset = AsignacionHorario.objects.all().select_related(
        'empleado', 'empleado__user', 'tipo_horario'
    )
    serializer_class = AsignacionHorarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()

        empleado_id = self.request.query_params.get('empleado', None)
        if empleado_id:
            queryset = queryset.filter(empleado_id=empleado_id)

        mes = self.request.query_params.get('mes', None)
        anio = self.request.query_params.get('anio', None)
        if mes and anio:
            queryset = queryset.filter(fecha__month=int(mes), fecha__year=int(anio))

        fecha = self.request.query_params.get('fecha', None)
        if fecha:
            queryset = queryset.filter(fecha=fecha)

        return queryset

    @action(detail=False, methods=['post'], url_path='asignar')
    def asignar(self, request):
        """Asignar o actualizar un horario para un empleado en una fecha"""
        empleado_id = request.data.get('empleado')
        fecha = request.data.get('fecha')
        tipo_horario_id = request.data.get('tipo_horario')

        if not all([empleado_id, fecha, tipo_horario_id]):
            return Response(
                {'error': 'Se requiere empleado, fecha y tipo_horario'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Si tipo_horario_id es 0 o null, eliminar la asignacion
        if not tipo_horario_id or str(tipo_horario_id) == '0':
            deleted, _ = AsignacionHorario.objects.filter(
                empleado_id=empleado_id, fecha=fecha
            ).delete()
            return Response({
                'success': True,
                'action': 'deleted' if deleted else 'no_change',
            })

        asignacion, created = AsignacionHorario.objects.update_or_create(
            empleado_id=empleado_id,
            fecha=fecha,
            defaults={
                'tipo_horario_id': tipo_horario_id,
                'creado_por': request.user,
            }
        )

        return Response({
            'success': True,
            'action': 'created' if created else 'updated',
            'asignacion': AsignacionHorarioSerializer(asignacion).data,
        })

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk_asignar(self, request):
        """Asignar un tipo de horario a multiples empleados/fechas"""
        serializer = AsignacionBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo_horario_id = serializer.validated_data['tipo_horario']
        empleados_ids = serializer.validated_data['empleados']
        fechas = serializer.validated_data['fechas']

        creados = 0
        actualizados = 0
        for emp_id in empleados_ids:
            for fecha in fechas:
                _, created = AsignacionHorario.objects.update_or_create(
                    empleado_id=emp_id,
                    fecha=fecha,
                    defaults={
                        'tipo_horario_id': tipo_horario_id,
                        'creado_por': request.user,
                    }
                )
                if created:
                    creados += 1
                else:
                    actualizados += 1

        return Response({
            'success': True,
            'creados': creados,
            'actualizados': actualizados,
            'total': creados + actualizados,
        })
