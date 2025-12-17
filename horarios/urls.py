from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HorarioViewSet

app_name = 'horarios'

router = DefaultRouter()
router.register(r'', HorarioViewSet, basename='horario')

urlpatterns = [
    path('', include(router.urls)),
]
