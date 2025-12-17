from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegistroAsistenciaViewSet

app_name = 'registros'

router = DefaultRouter()
router.register(r'', RegistroAsistenciaViewSet, basename='registro')

urlpatterns = [
    path('', include(router.urls)),
]
