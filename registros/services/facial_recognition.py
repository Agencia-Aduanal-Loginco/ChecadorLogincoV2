"""
Servicio de reconocimiento facial para el sistema de asistencias.
Usa face_recognition y OpenCV para procesar imágenes y reconocer rostros.
"""

import face_recognition
import cv2
import numpy as np
from PIL import Image
import io
from typing import Optional, Tuple, List, Dict
from django.core.files.uploadedfile import InMemoryUploadedFile
from empleados.models import Empleado


class FacialRecognitionService:
    """Servicio para manejar reconocimiento facial"""
    
    # Configuración
    FACE_TOLERANCE = 0.6  # Menor valor = más estricto (0.6 es el default)
    MIN_FACE_SIZE = (50, 50)  # Tamaño mínimo del rostro en píxeles
    MAX_FACES_ALLOWED = 1  # Máximo de rostros permitidos en una imagen de registro
    
    @staticmethod
    def load_image_from_file(image_file) -> Optional[np.ndarray]:
        """
        Carga una imagen desde un archivo Django UploadedFile o path.
        
        Args:
            image_file: Archivo de imagen (UploadedFile) o path
            
        Returns:
            numpy array con la imagen en formato RGB o None si hay error
        """
        try:
            if isinstance(image_file, InMemoryUploadedFile):
                # Convertir InMemoryUploadedFile a PIL Image
                image = Image.open(image_file)
                # Convertir a RGB si es necesario
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                # Convertir PIL Image a numpy array
                image_array = np.array(image)
                return image_array
            else:
                # Si es un path, cargar directamente
                image = face_recognition.load_image_file(image_file)
                return image
        except Exception as e:
            print(f"Error al cargar imagen: {str(e)}")
            return None
    
    @staticmethod
    def detect_faces(image: np.ndarray) -> List[Tuple]:
        """
        Detecta rostros en una imagen.
        
        Args:
            image: numpy array con la imagen
            
        Returns:
            Lista de ubicaciones de rostros (top, right, bottom, left)
        """
        face_locations = face_recognition.face_locations(image)
        return face_locations
    
    @staticmethod
    def validate_image_quality(image: np.ndarray) -> Tuple[bool, str]:
        """
        Valida que la imagen tenga la calidad suficiente para reconocimiento.
        
        Args:
            image: numpy array con la imagen
            
        Returns:
            Tupla (es_válida, mensaje)
        """
        if image is None or image.size == 0:
            return False, "Imagen vacía o inválida"
        
        # Verificar dimensiones mínimas
        height, width = image.shape[:2]
        if height < 100 or width < 100:
            return False, f"Imagen muy pequeña ({width}x{height}). Mínimo 100x100 píxeles"
        
        # Verificar si la imagen está muy oscura o muy clara
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        mean_brightness = np.mean(gray)
        
        if mean_brightness < 30:
            return False, "Imagen muy oscura. Mejore la iluminación"
        elif mean_brightness > 225:
            return False, "Imagen muy clara. Reduzca la iluminación"
        
        # Verificar desenfoque (usando Laplaciano)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            return False, "Imagen desenfocada. Use una imagen más nítida"
        
        return True, "Imagen válida"
    
    @staticmethod
    def extract_face_encoding(image: np.ndarray, validate: bool = True) -> Tuple[Optional[np.ndarray], str]:
        """
        Extrae el encoding facial de una imagen.
        
        Args:
            image: numpy array con la imagen
            validate: Si debe validar la calidad de la imagen
            
        Returns:
            Tupla (encoding o None, mensaje)
        """
        if validate:
            is_valid, message = FacialRecognitionService.validate_image_quality(image)
            if not is_valid:
                return None, message
        
        # Detectar rostros
        face_locations = FacialRecognitionService.detect_faces(image)
        
        if len(face_locations) == 0:
            return None, "No se detectó ningún rostro en la imagen"
        
        if len(face_locations) > FacialRecognitionService.MAX_FACES_ALLOWED:
            return None, f"Se detectaron {len(face_locations)} rostros. Solo debe haber uno"
        
        # Verificar tamaño del rostro
        top, right, bottom, left = face_locations[0]
        face_width = right - left
        face_height = bottom - top
        
        if face_width < FacialRecognitionService.MIN_FACE_SIZE[0] or \
           face_height < FacialRecognitionService.MIN_FACE_SIZE[1]:
            return None, f"Rostro muy pequeño ({face_width}x{face_height}). Acérquese a la cámara"
        
        # Extraer encoding
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if len(face_encodings) == 0:
            return None, "No se pudo extraer el encoding facial. Intente con otra imagen"
        
        return face_encodings[0], "Encoding extraído exitosamente"
    
    @staticmethod
    def compare_faces(known_encoding: np.ndarray, unknown_encoding: np.ndarray) -> Tuple[bool, float]:
        """
        Compara dos encodings faciales.
        
        Args:
            known_encoding: Encoding conocido
            unknown_encoding: Encoding a comparar
            
        Returns:
            Tupla (coincide, distancia/confianza)
        """
        # Calcular distancia facial
        face_distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
        
        # Convertir distancia a porcentaje de confianza (0-100)
        # face_distance va de 0 (idéntico) a 1+ (muy diferente)
        confidence = max(0, min(100, (1 - face_distance) * 100))
        
        # Verificar si coincide
        matches = face_recognition.compare_faces(
            [known_encoding],
            unknown_encoding,
            tolerance=FacialRecognitionService.FACE_TOLERANCE
        )
        
        return matches[0], confidence
    
    @staticmethod
    def recognize_employee(image: np.ndarray) -> Tuple[Optional[Empleado], float, str]:
        """
        Intenta reconocer a un empleado en una imagen.
        
        Args:
            image: numpy array con la imagen
            
        Returns:
            Tupla (empleado o None, confianza, mensaje)
        """
        # Extraer encoding de la imagen
        unknown_encoding, message = FacialRecognitionService.extract_face_encoding(image)
        
        if unknown_encoding is None:
            return None, 0.0, message
        
        # Obtener todos los empleados activos con rostro registrado
        empleados = Empleado.objects.filter(
            activo=True,
            embedding_rostro__isnull=False
        ).exclude(embedding_rostro=b'')
        
        if not empleados.exists():
            return None, 0.0, "No hay empleados registrados con reconocimiento facial"
        
        # Buscar coincidencia
        best_match = None
        best_confidence = 0.0
        
        for empleado in empleados:
            known_encoding = empleado.get_face_encoding()
            if known_encoding is None:
                continue
            
            matches, confidence = FacialRecognitionService.compare_faces(
                known_encoding,
                unknown_encoding
            )
            
            if matches and confidence > best_confidence:
                best_match = empleado
                best_confidence = confidence
        
        if best_match:
            return best_match, best_confidence, f"Empleado reconocido con {best_confidence:.1f}% de confianza"
        else:
            return None, 0.0, "No se encontró coincidencia con ningún empleado registrado"
    
    @staticmethod
    def register_employee_face(empleado: Empleado, image_file) -> Tuple[bool, str]:
        """
        Registra el rostro de un empleado.
        
        Args:
            empleado: Instancia del empleado
            image_file: Archivo de imagen
            
        Returns:
            Tupla (éxito, mensaje)
        """
        # Cargar imagen
        image = FacialRecognitionService.load_image_from_file(image_file)
        
        if image is None:
            return False, "No se pudo cargar la imagen"
        
        # Extraer encoding
        encoding, message = FacialRecognitionService.extract_face_encoding(image, validate=True)
        
        if encoding is None:
            return False, message
        
        # Guardar encoding en el empleado
        try:
            empleado.set_face_encoding(encoding)
            empleado.save()
            return True, "Rostro registrado exitosamente"
        except Exception as e:
            return False, f"Error al guardar el rostro: {str(e)}"
    
    @staticmethod
    def get_face_landmarks(image: np.ndarray) -> List[Dict]:
        """
        Obtiene los landmarks faciales de una imagen.
        Útil para debugging o funcionalidades avanzadas.
        
        Args:
            image: numpy array con la imagen
            
        Returns:
            Lista de diccionarios con landmarks
        """
        face_locations = FacialRecognitionService.detect_faces(image)
        if not face_locations:
            return []
        
        landmarks = face_recognition.face_landmarks(image, face_locations)
        return landmarks
