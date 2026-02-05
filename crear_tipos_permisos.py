#!/usr/bin/env python
"""
Script para crear tipos de permisos iniciales en el sistema
Basado en la tabla de fixtures iniciales
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'checador.settings')
django.setup()

from django.db import transaction


# Definición de tipos de permisos según la tabla
# Ajustado a los nombres de campos del modelo existente
TIPOS_PERMISOS = [
    {
        'codigo': 'VAC',
        'nombre': 'Vacaciones',
        'descripcion': 'Período de descanso anual con goce de sueldo',
        'requiere_evidencia': False,  # No
        'dias_maximos': 15,
        'dias_anticipacion': 7,
        'afecta_salario': True,  # Con goce (True = con goce)
        'color': '#3BB2F6',  # Azul
    },
    {
        'codigo': 'INC',
        'nombre': 'Incapacidad',
        'descripcion': 'Ausencia por motivos de salud con certificado médico',
        'requiere_evidencia': True,  # Si
        'dias_maximos': 30,
        'dias_anticipacion': 0,
        'afecta_salario': True,  # Con goce
        'color': '#EF4444',  # Rojo
    },
    {
        'codigo': 'PER',
        'nombre': 'Permiso Personal',
        'descripcion': 'Ausencia por asuntos personales con goce de sueldo',
        'requiere_evidencia': False,  # No
        'dias_maximos': 3,
        'dias_anticipacion': 1,
        'afecta_salario': True,  # Con goce
        'color': '#8B5CF6',  # Morado
    },
    {
        'codigo': 'ECO',
        'nombre': 'Días Económicos',
        'descripcion': 'Días de ausencia permitidos por necesidades económicas',
        'requiere_evidencia': False,  # No
        'dias_maximos': 3,
        'dias_anticipacion': 1,
        'afecta_salario': True,  # Con goce
        'color': '#10B981',  # Verde
    },
    {
        'codigo': 'SGS',
        'nombre': 'Permiso Sin Goce',
        'descripcion': 'Ausencia sin goce de sueldo por motivos personales',
        'requiere_evidencia': False,  # No
        'dias_maximos': 15,
        'dias_anticipacion': 3,
        'afecta_salario': False,  # Sin goce (False = sin goce)
        'color': '#6B7280',  # Gris
    },
]


def crear_modelo_tipo_permiso():
    """
    Crea el modelo TipoPermiso si no existe.
    Este código genera el modelo que debes agregar a permisos/models.py
    """
    modelo_codigo = '''
from django.db import models


class TipoPermiso(models.Model):
    """Modelo para definir tipos de permisos disponibles"""
    
    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código',
        help_text='Código corto del tipo de permiso (ej: VAC, INC)'
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre',
        help_text='Nombre descriptivo del tipo de permiso'
    )
    evidencia = models.BooleanField(
        default=False,
        verbose_name='Requiere Evidencia',
        help_text='Indica si el permiso requiere documentos de respaldo'
    )
    dias_max = models.IntegerField(
        verbose_name='Días Máximos',
        help_text='Número máximo de días permitidos'
    )
    anticipacion = models.IntegerField(
        verbose_name='Días de Anticipación',
        help_text='Días mínimos de anticipación requeridos'
    )
    con_goce = models.BooleanField(
        default=True,
        verbose_name='Con Goce de Sueldo',
        help_text='Indica si el permiso es con goce de sueldo'
    )
    color = models.CharField(
        max_length=7,
        verbose_name='Color (Hex)',
        help_text='Color para identificación visual (formato: #RRGGBB)',
        default='#6B7280'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Permiso'
        verbose_name_plural = 'Tipos de Permisos'
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class SolicitudPermiso(models.Model):
    """Modelo para solicitudes de permisos de empleados"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('cancelado', 'Cancelado'),
    ]
    
    empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.CASCADE,
        related_name='solicitudes_permiso',
        verbose_name='Empleado'
    )
    tipo_permiso = models.ForeignKey(
        TipoPermiso,
        on_delete=models.PROTECT,
        related_name='solicitudes',
        verbose_name='Tipo de Permiso'
    )
    fecha_inicio = models.DateField(verbose_name='Fecha de Inicio')
    fecha_fin = models.DateField(verbose_name='Fecha de Fin')
    dias_solicitados = models.IntegerField(
        verbose_name='Días Solicitados',
        help_text='Número de días hábiles solicitados'
    )
    motivo = models.TextField(
        verbose_name='Motivo',
        help_text='Descripción o justificación del permiso'
    )
    evidencia = models.FileField(
        upload_to='permisos/evidencias/',
        null=True,
        blank=True,
        verbose_name='Evidencia',
        help_text='Documento de respaldo (opcional según tipo de permiso)'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )
    aprobado_por = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permisos_aprobados',
        verbose_name='Aprobado Por'
    )
    fecha_aprobacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Aprobación'
    )
    comentarios_aprobacion = models.TextField(
        blank=True,
        verbose_name='Comentarios de Aprobación'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Solicitud de Permiso'
        verbose_name_plural = 'Solicitudes de Permisos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.empleado.codigo_empleado} - {self.tipo_permiso.codigo} ({self.fecha_inicio})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que fecha_fin >= fecha_inicio
        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError({
                'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio'
            })
        
        # Validar días máximos
        if self.dias_solicitados > self.tipo_permiso.dias_max:
            raise ValidationError({
                'dias_solicitados': f'Excede el máximo de {self.tipo_permiso.dias_max} días para este tipo de permiso'
            })
        
        # Validar anticipación
        from datetime import date, timedelta
        dias_anticipacion = (self.fecha_inicio - date.today()).days
        if dias_anticipacion < self.tipo_permiso.anticipacion:
            raise ValidationError({
                'fecha_inicio': f'Se requieren al menos {self.tipo_permiso.anticipacion} días de anticipación'
            })
    
    @property
    def puede_cancelar(self):
        """Verifica si la solicitud puede ser cancelada"""
        from datetime import date
        return self.estado == 'pendiente' and self.fecha_inicio > date.today()
'''
    
    print("="*80)
    print("CÓDIGO DEL MODELO TipoPermiso y SolicitudPermiso")
    print("="*80)
    print("\nAgrega este código a: permisos/models.py")
    print("-"*80)
    print(modelo_codigo)
    print("="*80)


def crear_tipos_permisos():
    """Crea los tipos de permisos en la base de datos"""
    
    # Intentar importar el modelo
    try:
        # Primero intentamos importar desde una app 'permisos'
        from permisos.models import TipoPermiso
        print("✓ Modelo TipoPermiso encontrado en app 'permisos'")
    except ImportError:
        try:
            # Si no existe, intentamos desde 'registros'
            from registros.models import TipoPermiso
            print("✓ Modelo TipoPermiso encontrado en app 'registros'")
        except ImportError:
            print("✗ ERROR: No se encontró el modelo TipoPermiso")
            print("\nPrimero debes:")
            print("1. Crear la app 'permisos' (si no existe): python manage.py startapp permisos")
            print("2. Agregar 'permisos' a INSTALLED_APPS en settings.py")
            print("3. Agregar el modelo TipoPermiso a permisos/models.py")
            print("\n" + "="*80)
            crear_modelo_tipo_permiso()
            print("\n4. Crear migraciones: python manage.py makemigrations permisos")
            print("5. Aplicar migraciones: python manage.py migrate")
            print("6. Ejecutar este script nuevamente")
            return False
    
    print("\n" + "="*80)
    print("CREANDO TIPOS DE PERMISOS")
    print("="*80 + "\n")
    
    with transaction.atomic():
        creados = 0
        actualizados = 0
        
        for tipo_data in TIPOS_PERMISOS:
            tipo, created = TipoPermiso.objects.update_or_create(
                codigo=tipo_data['codigo'],
                defaults={
                    'nombre': tipo_data['nombre'],
                    'descripcion': tipo_data['descripcion'],
                    'requiere_evidencia': tipo_data['requiere_evidencia'],
                    'dias_maximos': tipo_data['dias_maximos'],
                    'dias_anticipacion': tipo_data['dias_anticipacion'],
                    'afecta_salario': tipo_data['afecta_salario'],
                    'color': tipo_data['color'],
                    'activo': True,
                }
            )
            
            if created:
                creados += 1
                print(f"✓ Creado: {tipo.codigo} - {tipo.nombre}")
            else:
                actualizados += 1
                print(f"↻ Actualizado: {tipo.codigo} - {tipo.nombre}")
            
            # Mostrar detalles
            print(f"  • Evidencia: {'Sí' if tipo.requiere_evidencia else 'No'}")
            print(f"  • Días máx: {tipo.dias_maximos}")
            print(f"  • Anticipación: {tipo.dias_anticipacion} días")
            print(f"  • Con goce: {'Sí' if tipo.afecta_salario else 'No'}")
            print(f"  • Color: {tipo.color}")
            print()
    
    print("="*80)
    print(f"✓ Proceso completado")
    print(f"  - Tipos creados: {creados}")
    print(f"  - Tipos actualizados: {actualizados}")
    print(f"  - Total: {creados + actualizados}")
    print("="*80)
    
    return True


def mostrar_resumen():
    """Muestra un resumen de los tipos de permisos que se crearán"""
    print("\n" + "="*80)
    print("RESUMEN DE TIPOS DE PERMISOS A CREAR")
    print("="*80)
    print("\n{:<8} {:<20} {:<10} {:<10} {:<12} {:<10} {:<10}".format(
        "Código", "Nombre", "Evidencia", "Días Max", "Anticipación", "Con Goce", "Color"
    ))
    print("-"*80)
    
    for tipo in TIPOS_PERMISOS:
        print("{:<8} {:<20} {:<10} {:<10} {:<12} {:<10} {:<10}".format(
            tipo['codigo'],
            tipo['nombre'],
            "Sí" if tipo['requiere_evidencia'] else "No",
            str(tipo['dias_maximos']),
            str(tipo['dias_anticipacion']),
            "Sí" if tipo['afecta_salario'] else "No",
            tipo['color']
        ))
    
    print("="*80 + "\n")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("SCRIPT DE CREACIÓN DE TIPOS DE PERMISOS")
    print("="*80)
    
    # Mostrar resumen
    mostrar_resumen()
    
    # Crear tipos de permisos
    exito = crear_tipos_permisos()
    
    if exito:
        print("\n✓ Script ejecutado exitosamente")
    else:
        print("\n✗ Script terminó con errores")
        print("Sigue las instrucciones anteriores y vuelve a ejecutar")
