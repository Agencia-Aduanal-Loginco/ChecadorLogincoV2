from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def generar_reporte_excel(datos):
    """
    Genera archivo Excel con 2 hojas:
    - Hoja 1: Resumen (empleado, dias trabajados, retardos, faltas)
    - Hoja 2: Detalle de registros de asistencia
    """
    wb = openpyxl.Workbook()

    # Estilos comunes
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )
    retardo_fill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
    falta_fill = PatternFill(start_color='FECACA', end_color='FECACA', fill_type='solid')

    # === HOJA 1: Resumen ===
    ws1 = wb.active
    ws1.title = "Resumen"

    # Titulo
    ws1.merge_cells('A1:G1')
    titulo_cell = ws1['A1']
    titulo_cell.value = f"Reporte de Asistencia - {datos['fecha_inicio']} al {datos['fecha_fin']}"
    titulo_cell.font = Font(bold=True, size=14, color='1E3A5F')
    titulo_cell.alignment = Alignment(horizontal='center')

    # Info general
    ws1['A2'] = f"Dias laborales: {datos['dias_laborales']}"
    ws1['A2'].font = Font(size=10, italic=True)
    ws1['D2'] = f"Total empleados: {datos['total_empleados']}"
    ws1['D2'].font = Font(size=10, italic=True)

    # Headers de tabla
    headers = ['Codigo', 'Nombre', 'Departamento', 'Dias Trabajados', 'Retardos', 'Faltas', 'Horas Totales']
    for col_idx, header in enumerate(headers, 1):
        cell = ws1.cell(row=4, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Datos
    for row_idx, emp in enumerate(datos['datos_empleados'], 5):
        ws1.cell(row=row_idx, column=1, value=emp['codigo']).border = thin_border
        ws1.cell(row=row_idx, column=2, value=emp['nombre']).border = thin_border
        ws1.cell(row=row_idx, column=3, value=emp['departamento']).border = thin_border

        cell_dias = ws1.cell(row=row_idx, column=4, value=emp['dias_trabajados'])
        cell_dias.border = thin_border
        cell_dias.alignment = Alignment(horizontal='center')

        cell_ret = ws1.cell(row=row_idx, column=5, value=emp['retardos'])
        cell_ret.border = thin_border
        cell_ret.alignment = Alignment(horizontal='center')
        if emp['retardos'] > 0:
            cell_ret.fill = retardo_fill

        cell_fal = ws1.cell(row=row_idx, column=6, value=emp['faltas'])
        cell_fal.border = thin_border
        cell_fal.alignment = Alignment(horizontal='center')
        if emp['faltas'] > 0:
            cell_fal.fill = falta_fill

        cell_hrs = ws1.cell(row=row_idx, column=7, value=emp['horas_totales'])
        cell_hrs.border = thin_border
        cell_hrs.alignment = Alignment(horizontal='center')
        cell_hrs.number_format = '0.00'

    # Ajustar anchos
    ws1.column_dimensions['A'].width = 15
    ws1.column_dimensions['B'].width = 30
    ws1.column_dimensions['C'].width = 20
    ws1.column_dimensions['D'].width = 16
    ws1.column_dimensions['E'].width = 12
    ws1.column_dimensions['F'].width = 10
    ws1.column_dimensions['G'].width = 15

    # === HOJA 2: Detalle ===
    ws2 = wb.create_sheet("Detalle de Asistencia")

    # Titulo
    ws2.merge_cells('A1:H1')
    titulo2 = ws2['A1']
    titulo2.value = f"Detalle de Registros - {datos['fecha_inicio']} al {datos['fecha_fin']}"
    titulo2.font = Font(bold=True, size=14, color='1E3A5F')
    titulo2.alignment = Alignment(horizontal='center')

    # Headers
    headers2 = ['Fecha', 'Codigo', 'Nombre', 'Hora Entrada', 'Hora Salida', 'Horas Trabajadas', 'Retardo', 'Incidencia']
    for col_idx, header in enumerate(headers2, 1):
        cell = ws2.cell(row=3, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Recopilar todos los registros ordenados por fecha
    todos_registros = []
    for emp in datos['datos_empleados']:
        for reg in emp['registros']:
            todos_registros.append({
                'fecha': reg.fecha,
                'codigo': emp['codigo'],
                'nombre': emp['nombre'],
                'hora_entrada': reg.hora_entrada,
                'hora_salida': reg.hora_salida,
                'horas_trabajadas': reg.horas_trabajadas or 0,
                'retardo': reg.retardo,
                'incidencia': reg.get_incidencia_display() if reg.incidencia != 'ninguna' else '',
            })

    todos_registros.sort(key=lambda x: (x['fecha'], x['codigo']))

    for row_idx, reg in enumerate(todos_registros, 4):
        ws2.cell(row=row_idx, column=1, value=str(reg['fecha'])).border = thin_border
        ws2.cell(row=row_idx, column=2, value=reg['codigo']).border = thin_border
        ws2.cell(row=row_idx, column=3, value=reg['nombre']).border = thin_border

        cell_ent = ws2.cell(row=row_idx, column=4, value=str(reg['hora_entrada']) if reg['hora_entrada'] else '')
        cell_ent.border = thin_border
        cell_ent.alignment = Alignment(horizontal='center')

        cell_sal = ws2.cell(row=row_idx, column=5, value=str(reg['hora_salida']) if reg['hora_salida'] else '')
        cell_sal.border = thin_border
        cell_sal.alignment = Alignment(horizontal='center')

        cell_hrs = ws2.cell(row=row_idx, column=6, value=round(reg['horas_trabajadas'], 2))
        cell_hrs.border = thin_border
        cell_hrs.alignment = Alignment(horizontal='center')
        cell_hrs.number_format = '0.00'

        cell_ret = ws2.cell(row=row_idx, column=7, value='Si' if reg['retardo'] else '')
        cell_ret.border = thin_border
        cell_ret.alignment = Alignment(horizontal='center')
        if reg['retardo']:
            cell_ret.fill = retardo_fill

        cell_inc = ws2.cell(row=row_idx, column=8, value=reg['incidencia'])
        cell_inc.border = thin_border

    # Ajustar anchos
    ws2.column_dimensions['A'].width = 12
    ws2.column_dimensions['B'].width = 12
    ws2.column_dimensions['C'].width = 30
    ws2.column_dimensions['D'].width = 14
    ws2.column_dimensions['E'].width = 14
    ws2.column_dimensions['F'].width = 16
    ws2.column_dimensions['G'].width = 10
    ws2.column_dimensions['H'].width = 20

    # Guardar en memoria
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
