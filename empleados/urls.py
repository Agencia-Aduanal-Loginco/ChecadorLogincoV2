from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmpleadoViewSet, register_face_view, register_face_post, delete_face_post

app_name = 'empleados'

router = DefaultRouter()
router.register(r'', EmpleadoViewSet, basename='empleado')

urlpatterns = [
    # Vista web para registrar rostro
    path('<int:empleado_id>/registrar-rostro-web/', register_face_view, name='register_face'),
    # Endpoint POST para registrar rostro (con sesión Django)
    path('<int:empleado_id>/registrar-rostro-session/', register_face_post, name='register_face_post'),
    # Endpoint POST para eliminar rostro (con sesión Django)
    path('<int:empleado_id>/eliminar-rostro-session/', delete_face_post, name='delete_face_post'),
    # API endpoints
    path('', include(router.urls)),
]
