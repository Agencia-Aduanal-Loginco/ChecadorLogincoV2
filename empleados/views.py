from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
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
    
    @action(detail=True, methods=['post'], url_path='eliminar-rostro')
    def eliminar_rostro(self, request, pk=None):
        """
        Endpoint para eliminar el registro facial de un empleado.
        Útil cuando se registró un rostro incorrecto.
        """
        empleado = self.get_object()
        
        if not empleado.tiene_rostro_registrado:
            return Response({
                'success': False,
                'message': 'El empleado no tiene ningún rostro registrado'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            empleado.eliminar_rostro()
            return Response({
                'success': True,
                'message': 'Registro facial eliminado exitosamente. Puedes registrar un nuevo rostro.',
                'empleado': EmpleadoDetailSerializer(empleado).data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error al eliminar el rostro: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def register_face_view(request, empleado_id):
    """
    Vista para renderizar el template de registro facial.
    Requiere autenticación.
    """
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    
    # Verificar permisos: solo staff o el mismo empleado pueden registrar
    if not request.user.is_staff and request.user != empleado.user:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("No tienes permisos para acceder a esta página.")
    
    return render(request, 'register_face.html', {
        'empleado': empleado
    })


@login_required
def register_face_post(request, empleado_id):
    """
    Vista POST para registrar el rostro usando sesiones de Django.
    Alternativa al endpoint de API que requiere JWT.
    """
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
    
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    
    # Verificar permisos: solo staff o el mismo empleado pueden registrar
    if not request.user.is_staff and request.user != empleado.user:
        return JsonResponse({'success': False, 'message': 'No tienes permisos'}, status=403)
    
    # Verificar que se envió una foto
    if 'foto_rostro' not in request.FILES:
        return JsonResponse({'success': False, 'message': 'No se envió ninguna foto'}, status=400)
    
    foto_rostro = request.FILES['foto_rostro']
    
    # Usar el servicio de reconocimiento facial
    success, message = FacialRecognitionService.register_employee_face(
        empleado,
        foto_rostro
    )
    
    if success:
        # Guardar la foto también en el modelo
        empleado.foto_rostro = foto_rostro
        empleado.save()
        
        return JsonResponse({
            'success': True,
            'message': message,
        }, status=200)
    else:
        return JsonResponse({
            'success': False,
            'message': message
        }, status=400)


@login_required
def delete_face_post(request, empleado_id):
    """
    Vista POST para eliminar el rostro facial registrado.
    Usa sesiones de Django.
    """
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
    
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    
    # Verificar permisos: solo staff puede eliminar
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'No tienes permisos'}, status=403)
    
    if not empleado.tiene_rostro_registrado:
        return JsonResponse({
            'success': False,
            'message': 'El empleado no tiene ningún rostro registrado'
        }, status=400)
    
    try:
        empleado.eliminar_rostro()
        return JsonResponse({
            'success': True,
            'message': 'Registro facial eliminado exitosamente. Puedes registrar un nuevo rostro.',
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al eliminar el rostro: {str(e)}'
        }, status=500)
