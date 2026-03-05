from datetime import timedelta
from django.utils import timezone


def obtener_datos_inventario():
    """
    Snapshot actual del inventario de equipos de cómputo.
    No requiere rango de fechas ya que refleja el estado presente.
    """
    from it_tickets.models import EquipoComputo, MantenimientoEquipo

    hoy = timezone.now().date()
    hace_30_dias = hoy - timedelta(days=30)

    equipos = list(
        EquipoComputo.objects.select_related('empleado__user').order_by('marca', 'modelo')
    )

    # Conteo por estado
    por_estado = {'activo': 0, 'mantenimiento': 0, 'baja': 0}
    for eq in equipos:
        por_estado[eq.estado] = por_estado.get(eq.estado, 0) + 1

    # Equipos con mantenimiento vencido
    vencidos = [eq for eq in equipos if eq.mantenimiento_vencido]

    # Equipos que requieren mantenimiento pronto (<=30 dias)
    pronto = [eq for eq in equipos if eq.requiere_mantenimiento_pronto and not eq.mantenimiento_vencido]

    # Equipos sin ningún mantenimiento registrado
    ids_con_mantenimiento = set(
        MantenimientoEquipo.objects.values_list('equipo_id', flat=True).distinct()
    )
    sin_mantenimiento = [eq for eq in equipos if eq.id not in ids_con_mantenimiento]

    # Últimos mantenimientos realizados (30 días)
    ultimos_mantenimientos = list(
        MantenimientoEquipo.objects.select_related('equipo', 'equipo__empleado__user', 'registrado_por')
        .filter(fecha_realizado__gte=hace_30_dias)
        .order_by('-fecha_realizado')[:50]
    )

    return {
        'fecha_reporte': hoy,
        'total_equipos': len(equipos),
        'por_estado': por_estado,
        'equipos_vencidos': vencidos,
        'equipos_pronto': pronto,
        'equipos_sin_mantenimiento': sin_mantenimiento,
        'ultimos_mantenimientos': ultimos_mantenimientos,
    }
