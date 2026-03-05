def obtener_datos_permisos(fecha_inicio, fecha_fin):
    """
    Datos de solicitudes de permiso cuyo período se traslapa con el rango dado.
    """
    from permisos.models import SolicitudPermiso

    solicitudes = list(
        SolicitudPermiso.objects.filter(
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio,
        ).exclude(estado='borrador')
        .select_related('empleado__user', 'tipo_permiso', 'aprobador__user')
        .order_by('-fecha_creacion')
    )

    # Conteo por estado
    por_estado = {'pendiente': 0, 'aprobado': 0, 'rechazado': 0, 'cancelado': 0}
    for s in solicitudes:
        if s.estado in por_estado:
            por_estado[s.estado] += 1

    # Conteo y días por tipo de permiso
    por_tipo = {}
    for s in solicitudes:
        nombre_tipo = str(s.tipo_permiso)
        if nombre_tipo not in por_tipo:
            por_tipo[nombre_tipo] = {'solicitudes': 0, 'dias': 0}
        por_tipo[nombre_tipo]['solicitudes'] += 1
        por_tipo[nombre_tipo]['dias'] += s.dias_solicitados

    por_tipo_lista = sorted(por_tipo.items(), key=lambda x: x[1]['solicitudes'], reverse=True)

    # Días de permiso por empleado (solo aprobados)
    dias_por_empleado = {}
    for s in solicitudes:
        if s.estado == 'aprobado':
            nombre = s.empleado.nombre_completo if s.empleado else 'Desconocido'
            dias_por_empleado[nombre] = dias_por_empleado.get(nombre, 0) + s.dias_solicitados
    top_empleados = sorted(dias_por_empleado.items(), key=lambda x: x[1], reverse=True)[:10]

    # Pendientes de aprobación actualmente (snapshot, sin filtro de fecha)
    pendientes_ahora = list(
        SolicitudPermiso.objects.filter(estado='pendiente')
        .select_related('empleado__user', 'tipo_permiso')
        .order_by('fecha_creacion')
    )

    total_dias_aprobados = sum(
        s.dias_solicitados for s in solicitudes if s.estado == 'aprobado'
    )

    return {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_solicitudes': len(solicitudes),
        'por_estado': por_estado,
        'por_tipo': por_tipo_lista,
        'top_empleados': top_empleados,
        'total_dias_aprobados': total_dias_aprobados,
        'pendientes_ahora': pendientes_ahora,
        'solicitudes': solicitudes,
    }
