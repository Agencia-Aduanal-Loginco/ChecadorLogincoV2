from django.db.models import Avg, Count, F


def obtener_datos_tickets(fecha_inicio, fecha_fin):
    """
    Datos de tickets IT creados en el rango de fechas dado.
    """
    from it_tickets.models import Ticket, EstadoTicket, PrioridadTicket, CategoriaTicket

    tickets = list(
        Ticket.objects.filter(fecha_creacion__date__range=[fecha_inicio, fecha_fin])
        .select_related('empleado__user', 'asignado_a')
        .order_by('-fecha_creacion')
    )

    # Conteo por estado
    por_estado = {estado: 0 for estado, _ in EstadoTicket.choices}
    for t in tickets:
        por_estado[t.estado] = por_estado.get(t.estado, 0) + 1

    # Conteo por prioridad
    por_prioridad = {p: 0 for p, _ in PrioridadTicket.choices}
    por_prioridad['sin_asignar'] = 0
    for t in tickets:
        key = t.prioridad if t.prioridad else 'sin_asignar'
        por_prioridad[key] = por_prioridad.get(key, 0) + 1

    # Conteo por categoría
    por_categoria = {c: 0 for c, _ in CategoriaTicket.choices}
    for t in tickets:
        por_categoria[t.categoria] = por_categoria.get(t.categoria, 0) + 1

    # Tiempo promedio de resolución (solo tickets concluidos)
    concluidos = [t for t in tickets if t.estado == EstadoTicket.CONCLUIDO and t.fecha_resolucion]
    if concluidos:
        total_horas = sum(t.tiempo_resolucion_horas for t in concluidos)
        promedio_horas = round(total_horas / len(concluidos), 1)
    else:
        promedio_horas = None

    # Top empleados que más reportan
    conteo_empleados = {}
    for t in tickets:
        nombre = t.empleado.nombre_completo if t.empleado else 'Sin asignar'
        conteo_empleados[nombre] = conteo_empleados.get(nombre, 0) + 1
    top_empleados = sorted(conteo_empleados.items(), key=lambda x: x[1], reverse=True)[:10]

    # Tickets por técnico asignado
    conteo_tecnicos = {}
    for t in tickets:
        nombre = t.asignado_a.get_full_name() or t.asignado_a.username if t.asignado_a else 'Sin asignar'
        conteo_tecnicos[nombre] = conteo_tecnicos.get(nombre, 0) + 1
    por_tecnico = sorted(conteo_tecnicos.items(), key=lambda x: x[1], reverse=True)

    return {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_tickets': len(tickets),
        'por_estado': por_estado,
        'por_prioridad': por_prioridad,
        'por_categoria': por_categoria,
        'tickets_concluidos': len(concluidos),
        'promedio_horas_resolucion': promedio_horas,
        'top_empleados': top_empleados,
        'por_tecnico': por_tecnico,
        'tickets': tickets,
    }
