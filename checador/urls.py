"""
URL configuration for checador project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from registros.frontend_views import facial_recognition_page, facial_recognition_comida_page
from horarios.frontend_views import asignacion_horarios_view
from checador import views

# Importar vistas de nuevas apps
from organizacion.views import organigrama_view
from permisos.views import (
    mis_permisos_view,
    nueva_solicitud_view,
    detalle_permiso_view,
    aprobar_permisos_view,
    accion_permiso_view,
)
from visitas.views import (
    registrar_visita_view,
    verificar_qr_view,
    verificar_resultado_view,
    lista_visitas_view,
    detalle_visita_view,
    accion_visita_view,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Autenticacion web
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Vistas de empleados y registros (staff)
    path('empleados/', views.empleados_lista_view, name='empleados_lista'),
    path('registros/', views.registros_lista_view, name='registros_lista'),

    # Asignacion de horarios
    path('horarios/asignacion/', asignacion_horarios_view, name='asignacion_horarios'),

    # Marcar asistencia
    path('marcar-asistencia/', views.marcar_asistencia_view, name='marcar_asistencia'),

    # Pagina principal - Reconocimiento Facial
    path('', facial_recognition_page, name='home'),
    path('facial/', facial_recognition_page, name='facial_recognition'),
    path('checador/', facial_recognition_comida_page, name='facial_recognition_comida'),

    # Organizacion
    path('organigrama/', organigrama_view, name='organigrama'),

    # Permisos
    path('mis-permisos/', mis_permisos_view, name='mis_permisos'),
    path('permisos/nueva/', nueva_solicitud_view, name='nueva_solicitud'),
    path('permisos/<int:pk>/', detalle_permiso_view, name='detalle_permiso'),
    path('permisos/aprobar/', aprobar_permisos_view, name='aprobar_permisos'),
    path('permisos/<int:pk>/<str:accion>/', accion_permiso_view, name='accion_permiso'),

    # Visitas
    path('visitas/registrar/', registrar_visita_view, name='registrar_visita'),
    path('visitas/verificar/', verificar_qr_view, name='verificar_qr'),
    path('visitas/verificar/<uuid:codigo>/', verificar_resultado_view, name='verificar_resultado'),
    path('visitas/', lista_visitas_view, name='lista_visitas'),
    path('visitas/<int:pk>/', detalle_visita_view, name='detalle_visita'),
    path('visitas/<int:pk>/<str:accion>/', accion_visita_view, name='accion_visita'),

    # API de autenticacion
    path('api/auth/', include('authentication.urls')),

    # APIs principales
    path('api/empleados/', include('empleados.urls')),
    path('api/horarios/', include('horarios.urls')),
    path('api/registros/', include('registros.urls')),

    # APIs nuevas
    path('api/organizacion/', include('organizacion.urls')),
    path('api/permisos/', include('permisos.urls')),
    path('api/visitas/', include('visitas.urls')),

    # IT Tickets
    # API REST:   /api/it/equipos/, /api/it/tickets/, /api/it/mantenimientos/
    # Vistas web: /it/, /it/tickets/, /it/inventario/, /it/mantenimiento/calendario/
    path('', include('it_tickets.urls', namespace='it_tickets')),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
