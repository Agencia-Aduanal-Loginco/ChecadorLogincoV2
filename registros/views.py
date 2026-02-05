from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from .models import RegistroAsistencia
from empleados.models import Empleado
from .services import FacialRecognitionService
from .serializers import (
    RegistroAsistenciaSerializer,
    VerificarRostroSerializer,
    MarcarAsistenciaSerializer
)

# Zona horaria de México
MEXICO_TZ = ZoneInfo('America/Mexico_City')



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
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def marcar_salida_comida(self, request):
        """Marcar salida a comida con reconocimiento facial"""
        return self._marcar_asistencia(request, 'salida_comida')
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def marcar_entrada_comida(self, request):
        """Marcar entrada de comida con reconocimiento facial"""
        return self._marcar_asistencia(request, 'entrada_comida')
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verificar_rostro(self, request):
        """Verificar rostro y retornar estado del empleado sin marcar asistencia"""
        serializer = VerificarRostroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        foto = serializer.validated_data['foto']
        
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
        
        # Obtener hora y fecha actual en México
        ahora_mexico = timezone.now().astimezone(MEXICO_TZ)
        hoy = ahora_mexico.date()
        hora_actual = ahora_mexico.time()
        
        # Obtener o crear registro del día
        registro, created = RegistroAsistencia.objects.get_or_create(
            empleado=empleado,
            fecha=hoy
        )
        
        # Obtener horario del dia usando el nuevo servicio
        from horarios.services import obtener_horario_del_dia
        horario_data = obtener_horario_del_dia(empleado, hoy)

        # Obtener botones disponibles
        botones_disponibles = registro.obtener_botones_disponibles(hora_actual)

        # Preparar informacion del horario
        horario_info = None
        if horario_data:
            horario_info = {
                'tiene_comida': horario_data['tiene_comida'],
                'hora_entrada': horario_data['hora_entrada'].strftime('%H:%M') if horario_data['hora_entrada'] else None,
                'hora_salida': horario_data['hora_salida'].strftime('%H:%M') if horario_data['hora_salida'] else None,
                'hora_inicio_comida': horario_data['hora_inicio_comida'].strftime('%H:%M') if horario_data['hora_inicio_comida'] else None,
                'hora_fin_comida': horario_data['hora_fin_comida'].strftime('%H:%M') if horario_data['hora_fin_comida'] else None,
            }
        
        # Preparar estado del registro
        registro_estado = {
            'hora_entrada': registro.hora_entrada.strftime('%H:%M:%S') if registro.hora_entrada else None,
            'hora_salida_comida': registro.hora_salida_comida.strftime('%H:%M:%S') if registro.hora_salida_comida else None,
            'hora_entrada_comida': registro.hora_entrada_comida.strftime('%H:%M:%S') if registro.hora_entrada_comida else None,
            'hora_salida': registro.hora_salida.strftime('%H:%M:%S') if registro.hora_salida else None,
            'retardo': registro.retardo,
            'incidencia': registro.incidencia,
        }
        
        # Generar mensaje de estado
        mensaje_estado = self._generar_mensaje_estado(registro, horario_data, hora_actual)
        
        return Response({
            'success': True,
            'empleado': {
                'id': empleado.id,
                'codigo': empleado.codigo_empleado,
                'nombre': empleado.nombre_completo,
                'foto_rostro': request.build_absolute_uri(empleado.foto_rostro.url) if empleado.foto_rostro else None,
            },
            'horario': horario_info,
            'registro': registro_estado,
            'botones_disponibles': botones_disponibles,
            'hora_actual': hora_actual.strftime('%H:%M:%S'),
            'mensaje_estado': mensaje_estado,
            'confianza': f'{confianza:.1f}%',
        }, status=status.HTTP_200_OK)
    
    def _generar_mensaje_estado(self, registro, horario_data, hora_actual):
        """Genera mensaje descriptivo del estado actual del registro"""
        if not registro.hora_entrada:
            return "Sin registros el dia de hoy"

        mensajes = []
        mensajes.append(f"Entrada: {registro.hora_entrada.strftime('%H:%M')}")

        if registro.hora_salida_comida:
            mensajes.append(f"Salida a comer: {registro.hora_salida_comida.strftime('%H:%M')}")

        if registro.hora_entrada_comida:
            mensajes.append(f"Regreso de comer: {registro.hora_entrada_comida.strftime('%H:%M')}")

        if registro.hora_salida:
            mensajes.append(f"Salida: {registro.hora_salida.strftime('%H:%M')}")
            return " | ".join(mensajes) + " - Dia completo"

        # Indicar proxima accion esperada
        if not registro.hora_salida_comida and horario_data and horario_data['tiene_comida']:
            obj = horario_data['objeto']
            if hasattr(obj, 'esta_en_horario_comida') and obj.esta_en_horario_comida(hora_actual):
                mensajes.append("Puedes salir a comer o marcar salida final")

        return " | ".join(mensajes)
    
    def _marcar_asistencia(self, request, tipo):
        """Método auxiliar para marcar entrada/salida/comida"""
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
        
        # Obtener o crear registro del día (usando hora de México)
        ahora_mexico = timezone.now().astimezone(MEXICO_TZ)
        hoy = ahora_mexico.date()
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
        
        # Actualizar según el tipo (hora de México)
        ahora = ahora_mexico.time()
        
        if tipo == 'entrada':
            if registro.hora_entrada:
                return Response({
                    'success': False,
                    'message': f'Ya hay una entrada registrada hoy a las {registro.hora_entrada}'
                }, status=status.HTTP_400_BAD_REQUEST)
            registro.hora_entrada = ahora
            
        elif tipo == 'salida_comida':
            if not registro.hora_entrada:
                return Response({
                    'success': False,
                    'message': 'No hay entrada registrada para marcar salida a comer'
                }, status=status.HTTP_400_BAD_REQUEST)
            if registro.hora_salida_comida:
                return Response({
                    'success': False,
                    'message': f'Ya hay una salida a comer registrada hoy a las {registro.hora_salida_comida}'
                }, status=status.HTTP_400_BAD_REQUEST)
            registro.hora_salida_comida = ahora
            
        elif tipo == 'entrada_comida':
            if not registro.hora_salida_comida:
                return Response({
                    'success': False,
                    'message': 'No hay salida a comer registrada para marcar entrada de comida'
                }, status=status.HTTP_400_BAD_REQUEST)
            if registro.hora_entrada_comida:
                return Response({
                    'success': False,
                    'message': f'Ya hay una entrada de comida registrada hoy a las {registro.hora_entrada_comida}'
                }, status=status.HTTP_400_BAD_REQUEST)
            registro.hora_entrada_comida = ahora
            
        elif tipo == 'salida':
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
        
        # Preparar mensaje según tipo
        mensajes_tipo = {
            'entrada': 'Entrada',
            'salida_comida': 'Salida a comer',
            'entrada_comida': 'Regreso de comer',
            'salida': 'Salida final'
        }
        
        return Response({
            'success': True,
            'message': f'{mensajes_tipo[tipo]} registrada exitosamente',
            'empleado': empleado.nombre_completo,
            'codigo': empleado.codigo_empleado,
            'confianza': f'{confianza:.1f}%',
            'hora': ahora.strftime('%H:%M:%S'),
            'tipo': tipo,
            'registro': RegistroAsistenciaSerializer(registro).data
        }, status=status.HTTP_200_OK)
