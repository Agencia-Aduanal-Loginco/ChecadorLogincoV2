from datetime import timedelta

from horarios.services import obtener_horario_del_dia

from ..models import RegistroAsistencia


def obtener_registro_activo(empleado, fecha_hoy):
    """
    Resuelve sobre qué RegistroAsistencia debe operar un marcado de asistencia.

    Si el empleado tiene un turno nocturno del día anterior que sigue abierto
    (con hora_entrada pero sin hora_salida, y el horario asignado ese día
    tiene cruza_medianoche=True), se retorna ese registro para que la salida
    (o la comida) se marque ahí en vez de crear un registro nuevo para hoy.

    Retorna una tupla (registro, es_turno_nocturno_pendiente):
    - registro: la instancia de RegistroAsistencia encontrada, o None si no
      existe ninguna para hoy ni un turno nocturno pendiente de ayer (el
      llamador debe crear una nueva para fecha_hoy en ese caso).
    - es_turno_nocturno_pendiente: True si el registro retornado es el de
      ayer y corresponde a un turno nocturno todavía sin hora_salida.
    """
    fecha_ayer = fecha_hoy - timedelta(days=1)
    registro_ayer = RegistroAsistencia.objects.filter(
        empleado=empleado, fecha=fecha_ayer
    ).first()

    if registro_ayer and registro_ayer.hora_entrada and not registro_ayer.hora_salida:
        horario_ayer = obtener_horario_del_dia(empleado, fecha_ayer)
        if horario_ayer and getattr(horario_ayer['objeto'], 'cruza_medianoche', False):
            return registro_ayer, True

    registro_hoy = RegistroAsistencia.objects.filter(
        empleado=empleado, fecha=fecha_hoy
    ).first()
    return registro_hoy, False
