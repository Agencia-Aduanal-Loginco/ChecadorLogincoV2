from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TipoPermisoViewSet,
    SolicitudPermisoViewSet,
)

app_name = 'permisos'

router = DefaultRouter()
router.register(r'tipos', TipoPermisoViewSet, basename='tipo-permiso')
router.register(r'solicitudes', SolicitudPermisoViewSet, basename='solicitud-permiso')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
]
