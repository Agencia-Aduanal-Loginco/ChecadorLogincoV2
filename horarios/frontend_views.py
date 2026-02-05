import calendar
from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from empleados.models import Empleado
from organizacion.models import Departamento
from .models import TipoHorario, AsignacionHorario


@login_required
@user_passes_test(lambda u: u.is_staff)
def asignacion_horarios_view(request):
    """Vista tipo Excel para asignar horarios a empleados por dia del mes"""
    from django.utils import timezone
    from zoneinfo import ZoneInfo

    MEXICO_TZ = ZoneInfo('America/Mexico_City')
    ahora = timezone.now().astimezone(MEXICO_TZ)

    mes = int(request.GET.get('mes', ahora.month))
    anio = int(request.GET.get('anio', ahora.year))
    departamento_id = request.GET.get('departamento', '')

    # Generar dias del mes
    nombres_dia = ['L', 'M', 'Mi', 'J', 'V', 'S', 'D']
    num_dias = calendar.monthrange(anio, mes)[1]
    dias = []
    for d in range(1, num_dias + 1):
        fecha = date(anio, mes, d)
        dias.append({
            'numero': d,
            'nombre_corto': nombres_dia[fecha.weekday()],
            'fecha': fecha.isoformat(),
            'es_fin_semana': fecha.weekday() >= 5,
        })

    # Empleados filtrados
    empleados_qs = Empleado.objects.filter(activo=True).select_related(
        'user', 'departamento_obj', 'horario_predeterminado'
    ).order_by('codigo_empleado')
    if departamento_id:
        empleados_qs = empleados_qs.filter(departamento_obj_id=departamento_id)

    # Cargar asignaciones del mes
    fecha_inicio = date(anio, mes, 1)
    fecha_fin = date(anio, mes, num_dias)
    asignaciones = AsignacionHorario.objects.filter(
        fecha__range=[fecha_inicio, fecha_fin],
        empleado__in=empleados_qs
    ).select_related('tipo_horario')

    # Diccionario {(empleado_id, 'YYYY-MM-DD'): asignacion}
    asignaciones_dict = {}
    for a in asignaciones:
        asignaciones_dict[(a.empleado_id, a.fecha.isoformat())] = {
            'tipo_horario_id': a.tipo_horario_id,
            'codigo': a.tipo_horario.codigo,
            'color': a.tipo_horario.color,
            'nombre': a.tipo_horario.nombre,
        }

    # Preparar datos de empleados con sus asignaciones
    empleados_data = []
    for emp in empleados_qs:
        emp_asignaciones = {}
        for dia in dias:
            key = (emp.id, dia['fecha'])
            if key in asignaciones_dict:
                emp_asignaciones[dia['fecha']] = asignaciones_dict[key]
            elif emp.horario_predeterminado:
                emp_asignaciones[dia['fecha']] = {
                    'tipo_horario_id': emp.horario_predeterminado_id,
                    'codigo': emp.horario_predeterminado.codigo,
                    'color': emp.horario_predeterminado.color,
                    'nombre': emp.horario_predeterminado.nombre,
                    'es_predeterminado': True,
                }
        empleados_data.append({
            'id': emp.id,
            'codigo': emp.codigo_empleado,
            'nombre': emp.nombre_completo,
            'departamento': emp.departamento_obj.nombre if emp.departamento_obj else emp.departamento,
            'horario_pred_id': emp.horario_predeterminado_id,
            'asignaciones': emp_asignaciones,
        })

    # Tipos de horario disponibles
    tipos_horario = list(TipoHorario.objects.filter(activo=True).values(
        'id', 'codigo', 'nombre', 'color', 'hora_entrada', 'hora_salida'
    ))

    # Departamentos para filtro
    departamentos = Departamento.objects.all().order_by('nombre')

    # Navegacion de meses
    nombres_meses = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]

    if mes > 1:
        mes_ant, anio_ant = mes - 1, anio
    else:
        mes_ant, anio_ant = 12, anio - 1

    if mes < 12:
        mes_sig, anio_sig = mes + 1, anio
    else:
        mes_sig, anio_sig = 1, anio + 1

    context = {
        'mes': mes,
        'anio': anio,
        'nombre_mes': nombres_meses[mes],
        'dias': dias,
        'empleados_data': empleados_data,
        'tipos_horario': tipos_horario,
        'departamentos': departamentos,
        'departamento_id': departamento_id,
        'mes_anterior': mes_ant,
        'anio_anterior': anio_ant,
        'mes_siguiente': mes_sig,
        'anio_siguiente': anio_sig,
    }
    return render(request, 'horarios/asignacion_horarios.html', context)
