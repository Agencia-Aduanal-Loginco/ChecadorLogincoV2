from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import Empleado
from .serializers import (
    EmpleadoListSerializer,
    EmpleadoDetailSerializer,
    EmpleadoCreateSerializer,
    EmpleadoUpdateSerializer,
    RegistrarRostroSerializer
)
from registros.services import FacialRecognitionService


class EmpleadoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de empleados.
    
    list: Listar todos los empleados
    create: Crear nuevo empleado
    retrieve: Obtener detalle de empleado
    update: Actualizar empleado completo
    partial_update: Actualizar empleado parcial
    destroy: Eliminar empleado
    registrar_rostro: Registrar rostro facial del empleado
    """
    queryset = Empleado.objects.all().select_related('user')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EmpleadoListSerializer
        elif self.action == 'create':
            return EmpleadoCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EmpleadoUpdateSerializer
        elif self.action == 'registrar_rostro':
            return RegistrarRostroSerializer
        return EmpleadoDetailSerializer
    
    def get_queryset(self):
        """
        Filtra el queryset según parámetros de búsqueda
        """
        queryset = super().get_queryset()
        
        # Filtrar por activo/inactivo
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            activo_bool = activo.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(activo=activo_bool)
        
        # Filtrar por departamento
        departamento = self.request.query_params.get('departamento', None)
        if departamento:
            queryset = queryset.filter(departamento__icontains=departamento)
        
        # Buscar por código o nombre
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(codigo_empleado__icontains=search) |
                models.Q(user__first_name__icontains=search) |
                models.Q(user__last_name__icontains=search) |
                models.Q(user__username__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='registrar-rostro')
    def registrar_rostro(self, request, pk=None):
        """
        Endpoint para registrar o actualizar el rostro de un empleado.
        
        Se espera un archivo de imagen en el campo 'foto_rostro'.
        """
        empleado = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        foto_rostro = serializer.validated_data['foto_rostro']
        
        # Usar el servicio de reconocimiento facial
        success, message = FacialRecognitionService.register_employee_face(
            empleado,
            foto_rostro
        )
        
        if success:
            # Guardar la foto también en el modelo
            empleado.foto_rostro = foto_rostro
            empleado.save()
            
            return Response({
                'success': True,
                'message': message,
                'empleado': EmpleadoDetailSerializer(empleado).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)
