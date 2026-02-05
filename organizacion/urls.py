from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartamentoViewSet, RelacionSupervisionViewSet, organigrama_view

app_name = 'organizacion'

router = DefaultRouter()
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')
router.register(r'relaciones', RelacionSupervisionViewSet, basename='relacion')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
]
