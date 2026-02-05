from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from empleados.models import Empleado
from registros.models import RegistroAsistencia
from permisos.models import SolicitudPermiso
from visitas.models import Visita


def login_view(request):
    """Vista de inicio de sesión"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.get_full_name() or user.username}!')
            
            # Redirigir a la página solicitada o al dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    
    return render(request, 'auth/login.html')


def register_view(request):
    """Vista de registro de nuevos usuarios"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        codigo_empleado = request.POST.get('codigo_empleado')
        departamento = request.POST.get('departamento')
        puesto = request.POST.get('puesto')
        
        # Validaciones
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'auth/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe.')
            return render(request, 'auth/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return render(request, 'auth/register.html')
        
        if Empleado.objects.filter(codigo_empleado=codigo_empleado).exists():
            messages.error(request, 'El código de empleado ya está en uso.')
            return render(request, 'auth/register.html')
        
        try:
            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Crear empleado
            empleado = Empleado.objects.create(
                user=user,
                codigo_empleado=codigo_empleado,
                departamento=departamento,
                puesto=puesto or ''
            )
            
            messages.success(request, '¡Registro exitoso! Ahora registra tu rostro para completar tu perfil.')
            
            # Iniciar sesión automáticamente
            login(request, user)
            
            # Redirigir al registro de rostro
            return redirect('empleados:register_face', empleado_id=empleado.pk)
            
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
    
    return render(request, 'auth/register.html')


def logout_view(request):
    """Vista de cierre de sesión"""
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """Dashboard principal"""
    context = {
        'today': timezone.now().date(),
    }
    
    # Obtener empleado del usuario actual
    try:
        empleado = request.user.empleado
        context['empleado'] = empleado
        
        # Obtener registro de hoy
        hoy = timezone.now().date()
        registro_hoy = RegistroAsistencia.objects.filter(
            empleado=empleado,
            fecha=hoy
        ).first()
        context['registro_hoy'] = registro_hoy
        
        # Estadísticas del mes actual
        primer_dia_mes = hoy.replace(day=1)
        registros_mes = RegistroAsistencia.objects.filter(
            empleado=empleado,
            fecha__gte=primer_dia_mes,
            fecha__lte=hoy
        )
        
        context['dias_trabajados'] = registros_mes.filter(hora_entrada__isnull=False).count()
        context['retardos_mes'] = registros_mes.filter(retardo=True).count()
        context['horas_totales'] = sum([r.horas_trabajadas for r in registros_mes])
        
        # Últimos 7 registros
        context['ultimos_registros'] = RegistroAsistencia.objects.filter(
            empleado=empleado
        ).order_by('-fecha')[:7]
        
    except Empleado.DoesNotExist:
        context['empleado'] = None
        messages.warning(request, 'No tienes un perfil de empleado asociado.')
    
    # Permisos del empleado
    if context.get('empleado'):
        empleado = context['empleado']
        # Ultimos permisos del empleado
        context['permisos_recientes'] = SolicitudPermiso.objects.filter(
            empleado=empleado
        ).select_related('tipo_permiso').order_by('-fecha_creacion')[:5]

        # Conteo de permisos pendientes propios
        context['mis_permisos_pendientes'] = SolicitudPermiso.objects.filter(
            empleado=empleado,
            estado='pendiente'
        ).count()

    # Estadisticas para staff
    if request.user.is_staff:
        hoy = timezone.now().date()
        context['total_empleados'] = Empleado.objects.filter(activo=True).count()
        context['registros_hoy'] = RegistroAsistencia.objects.filter(fecha=hoy).count()
        context['empleados_sin_rostro'] = Empleado.objects.filter(
            activo=True,
            embedding_rostro__isnull=True
        ).count()

        # Permisos pendientes de aprobar
        context['permisos_por_aprobar'] = SolicitudPermiso.objects.filter(
            estado='pendiente'
        ).count()

        # Visitas del dia
        context['visitas_hoy'] = Visita.objects.filter(fecha_programada=hoy).count()
        context['visitas_pendientes'] = Visita.objects.filter(
            fecha_programada=hoy,
            estado='pendiente'
        ).count()
        context['visitas_en_sitio'] = Visita.objects.filter(
            fecha_programada=hoy,
            estado='en_sitio'
        ).count()

    return render(request, 'dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def empleados_lista_view(request):
    """Lista de empleados (solo para staff)"""
    search = request.GET.get('search', '')
    departamento = request.GET.get('departamento', '')
    
    empleados = Empleado.objects.select_related('user').filter(activo=True)
    
    if search:
        empleados = empleados.filter(
            Q(codigo_empleado__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    if departamento:
        empleados = empleados.filter(departamento__icontains=departamento)
    
    # Obtener lista de departamentos para el filtro
    departamentos = Empleado.objects.filter(activo=True).values_list('departamento', flat=True).distinct()
    
    context = {
        'empleados': empleados.order_by('codigo_empleado'),
        'departamentos': departamentos,
        'search': search,
        'departamento_selected': departamento,
    }
    
    return render(request, 'empleados/lista.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def registros_lista_view(request):
    """Lista de registros de asistencia (solo para staff)"""
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    empleado_id = request.GET.get('empleado', '')
    
    # Por defecto, mostrar registros del mes actual
    if not fecha_inicio:
        fecha_inicio = timezone.now().date().replace(day=1)
    else:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    
    if not fecha_fin:
        fecha_fin = timezone.now().date()
    else:
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    
    registros = RegistroAsistencia.objects.select_related('empleado__user').filter(
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    )
    
    if empleado_id:
        registros = registros.filter(empleado_id=empleado_id)
    
    # Estadísticas
    stats = {
        'total_registros': registros.count(),
        'retardos': registros.filter(retardo=True).count(),
        'horas_totales': sum([r.horas_trabajadas for r in registros]),
        'registros_completos': registros.filter(hora_entrada__isnull=False, hora_salida__isnull=False).count(),
    }
    
    empleados = Empleado.objects.filter(activo=True).order_by('codigo_empleado')
    
    context = {
        'registros': registros.order_by('-fecha', '-hora_entrada'),
        'empleados': empleados,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
        'empleado_selected': empleado_id,
        'stats': stats,
    }
    
    return render(request, 'registros/lista.html', context)


@login_required
def marcar_asistencia_view(request):
    """Vista para marcar asistencia (redirige a facial recognition)"""
    return redirect('facial_recognition')
