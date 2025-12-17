from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Horario
from .serializers import (
    HorarioSerializer,
    HorarioCreateUpdateSerializer,
    HorarioBulkCreateSerializer
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
        
        # Filtrar por empleado
        empleado_id = self.request.query_params.get('empleado', None)
        if empleado_id:
            queryset = queryset.filter(empleado_id=empleado_id)
        
        # Filtrar por día de la semana
        dia_semana = self.request.query_params.get('dia_semana', None)
        if dia_semana:
            queryset = queryset.filter(dia_semana=dia_semana)
        
        # Filtrar por activo
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Crear múltiples horarios para un empleado"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        horarios = serializer.save()
        
        return Response(
            HorarioSerializer(horarios, many=True).data,
            status=status.HTTP_201_CREATED
        )
