from datetime import timedelta

from empleados.models import Empleado
from registros.models import RegistroAsistencia


def contar_dias_laborales(fecha_inicio, fecha_fin):
    """Cuenta dias laborales (lunes a viernes) en un rango"""
    dias = 0
    actual = fecha_inicio
    while actual <= fecha_fin:
        if actual.weekday() < 5:  # 0=lunes, 4=viernes
            dias += 1
        actual += timedelta(days=1)
    return dias


def obtener_datos_reporte(fecha_inicio, fecha_fin):
    """Obtiene todos los datos necesarios para generar un reporte de asistencia"""
    empleados = Empleado.objects.filter(activo=True).select_related(
        'user', 'departamento_obj'
    ).order_by('codigo_empleado')

    registros = list(RegistroAsistencia.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin],
        empleado__activo=True
    ).select_related('empleado', 'empleado__user'))

    dias_laborales = contar_dias_laborales(fecha_inicio, fecha_fin)

    # Indexar registros por empleado
    registros_por_empleado = {}
    for r in registros:
        registros_por_empleado.setdefault(r.empleado_id, []).append(r)

    datos_empleados = []
    for empleado in empleados:
        regs = registros_por_empleado.get(empleado.id, [])

        dias_trabajados = len([r for r in regs if r.hora_entrada])
        retardos = len([r for r in regs if r.retardo])
        faltas = max(0, dias_laborales - dias_trabajados)
        horas_totales = sum(r.horas_trabajadas or 0 for r in regs)

        datos_empleados.append({
            'empleado': empleado,
            'codigo': empleado.codigo_empleado,
            'nombre': empleado.nombre_completo,
            'departamento': empleado.departamento_obj.nombre if empleado.departamento_obj else empleado.departamento,
            'dias_trabajados': dias_trabajados,
            'retardos': retardos,
            'faltas': faltas,
            'horas_totales': round(horas_totales, 2),
            'registros': regs,
        })

    # Top 5 retardos
    top_retardos = sorted(
        [d for d in datos_empleados if d['retardos'] > 0],
        key=lambda x: x['retardos'],
        reverse=True
    )[:5]

    # Empleados con faltas
    empleados_con_faltas = [d for d in datos_empleados if d['faltas'] > 0]

    return {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'dias_laborales': dias_laborales,
        'datos_empleados': datos_empleados,
        'top_retardos': top_retardos,
        'empleados_con_faltas': empleados_con_faltas,
        'total_empleados': len(datos_empleados),
        'total_registros': len(registros),
    }
