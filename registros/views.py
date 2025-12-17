from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import datetime, date
from .models import RegistroAsistencia
from empleados.models import Empleado
from .services import FacialRecognitionService
from rest_framework import serializers as rest_serializers


class RegistroAsistenciaSerializer(rest_serializers.ModelSerializer):
    """Serializer para registros de asistencia"""
    empleado_nombre = rest_serializers.CharField(source='empleado.nombre_completo', read_only=True)
    empleado_codigo = rest_serializers.CharField(source='empleado.codigo_empleado', read_only=True)
    esta_completo = rest_serializers.ReadOnlyField()
    tiempo_trabajado_str = rest_serializers.ReadOnlyField()
    
    class Meta:
        model = RegistroAsistencia
        fields = '__all__'
        read_only_fields = ('id', 'fecha_creacion', 'fecha_actualizacion', 'horas_trabajadas', 'retardo')


class MarcarAsistenciaSerializer(rest_serializers.Serializer):
    """Serializer para marcar asistencia con reconocimiento facial"""
    foto = rest_serializers.ImageField(required=True)
    tipo = rest_serializers.ChoiceField(choices=['entrada', 'salida'], required=True)
    latitud = rest_serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitud = rest_serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    ubicacion = rest_serializers.CharField(required=False, allow_blank=True)


class RegistroAsistenciaViewSet(viewsets.ModelViewSet):
    """ViewSet para registros de asistencia"""
    queryset = RegistroAsistencia.objects.all().select_related('empleado', 'empleado__user')
    permission_classes = [IsAuthenticated]
    serializer_class = RegistroAsistenciaSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por empleado
        empleado_id = self.request.query_params.get('empleado', None)
        if empleado_id:
            queryset = queryset.filter(empleado_id=empleado_id)
        
        # Filtrar por fecha
        fecha = self.request.query_params.get('fecha', None)
        if fecha:
            queryset = queryset.filter(fecha=fecha)
        
        # Filtrar por rango de fechas
        fecha_inicio = self.request.query_params.get('fecha_inicio', None)
        fecha_fin = self.request.query_params.get('fecha_fin', None)
        if fecha_inicio and fecha_fin:
            queryset = queryset.filter(fecha__range=[fecha_inicio, fecha_fin])
        
        return queryset.order_by('-fecha', '-hora_entrada')
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def marcar_entrada(self, request):
        """Marcar entrada con reconocimiento facial"""
        return self._marcar_asistencia(request, 'entrada')
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def marcar_salida(self, request):
        """Marcar salida con reconocimiento facial"""
        return self._marcar_asistencia(request, 'salida')
    
    def _marcar_asistencia(self, request, tipo):
        """Método auxiliar para marcar entrada/salida"""
        serializer = MarcarAsistenciaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        foto = serializer.validated_data['foto']
        latitud = serializer.validated_data.get('latitud')
        longitud = serializer.validated_data.get('longitud')
        ubicacion = serializer.validated_data.get('ubicacion', '')
        
        # Cargar y reconocer rostro
        image = FacialRecognitionService.load_image_from_file(foto)
        if image is None:
            return Response({
                'success': False,
                'message': 'No se pudo cargar la imagen'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        empleado, confianza, mensaje = FacialRecognitionService.recognize_employee(image)
        
        if not empleado:
            return Response({
                'success': False,
                'message': mensaje
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Obtener o crear registro del día
        hoy = timezone.now().date()
        registro, created = RegistroAsistencia.objects.get_or_create(
            empleado=empleado,
            fecha=hoy,
            defaults={
                'reconocimiento_facial': True,
                'confianza_reconocimiento': confianza,
                'latitud': latitud,
                'longitud': longitud,
                'ubicacion': ubicacion
            }
        )
        
        # Actualizar según el tipo
        ahora = timezone.now().time()
        if tipo == 'entrada':
            if registro.hora_entrada:
                return Response({
                    'success': False,
                    'message': f'Ya hay una entrada registrada hoy a las {registro.hora_entrada}'
                }, status=status.HTTP_400_BAD_REQUEST)
            registro.hora_entrada = ahora
        else:  # salida
            if not registro.hora_entrada:
                return Response({
                    'success': False,
                    'message': 'No hay entrada registrada para marcar salida'
                }, status=status.HTTP_400_BAD_REQUEST)
            if registro.hora_salida:
                return Response({
                    'success': False,
                    'message': f'Ya hay una salida registrada hoy a las {registro.hora_salida}'
                }, status=status.HTTP_400_BAD_REQUEST)
            registro.hora_salida = ahora
        
        # Guardar foto
        registro.foto_registro = foto
        registro.reconocimiento_facial = True
        registro.confianza_reconocimiento = confianza
        registro.save()
        
        return Response({
            'success': True,
            'message': f'{tipo.capitalize()} registrada exitosamente',
            'empleado': empleado.nombre_completo,
            'codigo': empleado.codigo_empleado,
            'confianza': f'{confianza:.1f}%',
            'hora': ahora.strftime('%H:%M:%S'),
            'registro': RegistroAsistenciaSerializer(registro).data
        }, status=status.HTTP_200_OK)
