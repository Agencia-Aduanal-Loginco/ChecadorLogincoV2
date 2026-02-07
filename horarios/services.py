from .models import AsignacionHorario


def obtener_horario_del_dia(empleado, fecha):
    """
    Resuelve el horario aplicable para un empleado en una fecha dada.

    Prioridad:
    1. AsignacionHorario especifica para la fecha
    2. Horario semanal existente (por dia_semana)
    3. horario_predeterminado del empleado (TipoHorario)

    Retorna dict con los campos del horario o None.
    """
    # 1. Buscar asignacion especifica para la fecha
    asignacion = AsignacionHorario.objects.filter(
        empleado=empleado, fecha=fecha
    ).select_related('tipo_horario').first()

    if asignacion:
        th = asignacion.tipo_horario
        return {
            'hora_entrada': th.hora_entrada,
            'hora_salida': th.hora_salida,
            'tolerancia_minutos': th.tolerancia_minutos,
            'tiene_comida': th.tiene_comida,
            'hora_inicio_comida': th.hora_inicio_comida,
            'hora_fin_comida': th.hora_fin_comida,
            'nombre': th.nombre,
            'fuente': 'asignacion',
            'objeto': th,
        }

    # 2. Buscar horario por dia de semana (modelo existente)
    dia_semana = fecha.isoweekday()
    horario = empleado.horarios.filter(dia_semana=dia_semana, activo=True).first()
    if horario:
        return {
            'hora_entrada': horario.hora_entrada,
            'hora_salida': horario.hora_salida,
            'tolerancia_minutos': horario.tolerancia_minutos,
            'tiene_comida': horario.tiene_comida,
            'hora_inicio_comida': horario.hora_inicio_comida,
            'hora_fin_comida': horario.hora_fin_comida,
            'nombre': None,
            'fuente': 'semanal',
            'objeto': horario,
        }

    # 3. Horario predeterminado del empleado según día de la semana
    if dia_semana == 6:  # Sábado
        if empleado.descansa_sabado:
            return None
        if empleado.horario_sabado:
            th = empleado.horario_sabado
            return {
                'hora_entrada': th.hora_entrada,
                'hora_salida': th.hora_salida,
                'tolerancia_minutos': th.tolerancia_minutos,
                'tiene_comida': th.tiene_comida,
                'hora_inicio_comida': th.hora_inicio_comida,
                'hora_fin_comida': th.hora_fin_comida,
                'nombre': th.nombre,
                'fuente': 'predeterminado_sabado',
                'objeto': th,
            }
    elif dia_semana == 7:  # Domingo
        if empleado.descansa_domingo:
            return None
        if empleado.horario_domingo:
            th = empleado.horario_domingo
            return {
                'hora_entrada': th.hora_entrada,
                'hora_salida': th.hora_salida,
                'tolerancia_minutos': th.tolerancia_minutos,
                'tiene_comida': th.tiene_comida,
                'hora_inicio_comida': th.hora_inicio_comida,
                'hora_fin_comida': th.hora_fin_comida,
                'nombre': th.nombre,
                'fuente': 'predeterminado_domingo',
                'objeto': th,
            }
    else:  # Lunes a Viernes (1-5)
        if empleado.horario_predeterminado:
            th = empleado.horario_predeterminado
            return {
                'hora_entrada': th.hora_entrada,
                'hora_salida': th.hora_salida,
                'tolerancia_minutos': th.tolerancia_minutos,
                'tiene_comida': th.tiene_comida,
                'hora_inicio_comida': th.hora_inicio_comida,
                'hora_fin_comida': th.hora_fin_comida,
                'nombre': th.nombre,
                'fuente': 'predeterminado',
                'objeto': th,
            }

    return None
