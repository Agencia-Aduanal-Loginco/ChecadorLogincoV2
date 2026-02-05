from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MotivoVisitaViewSet,
    VisitaViewSet,
    api_verificar_qr,
    api_registrar_movimiento,
)

app_name = 'visitas'

router = DefaultRouter()
router.register(r'motivos', MotivoVisitaViewSet, basename='motivo-visita')
router.register(r'visitas', VisitaViewSet, basename='visita')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    path('api/verificar-qr/', api_verificar_qr, name='api-verificar-qr'),
    path('api/registrar-movimiento/', api_registrar_movimiento, name='api-registrar-movimiento'),
]
