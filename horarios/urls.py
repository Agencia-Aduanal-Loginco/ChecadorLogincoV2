from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HorarioViewSet, TipoHorarioViewSet, AsignacionHorarioViewSet

app_name = 'horarios'

router = DefaultRouter()
router.register(r'tipos', TipoHorarioViewSet, basename='tipo-horario')
router.register(r'asignaciones', AsignacionHorarioViewSet, basename='asignacion-horario')
router.register(r'', HorarioViewSet, basename='horario')

urlpatterns = [
    path('', include(router.urls)),
]
