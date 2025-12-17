from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmpleadoViewSet

app_name = 'empleados'

router = DefaultRouter()
router.register(r'', EmpleadoViewSet, basename='empleado')

urlpatterns = [
    path('', include(router.urls)),
]
