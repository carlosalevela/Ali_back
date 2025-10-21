from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestGrado9ViewSet,ResultadoTest9PorIDView,TestsDeUsuarioPorAdminView,FiltroPorTecnicoView


router = DefaultRouter()
router.register(r'', TestGrado9ViewSet, basename='test_grado9')

urlpatterns = [
    path('resultado/<int:test_id>/', ResultadoTest9PorIDView.as_view(), name='resultado_test_9'),
    path('usuario/<int:user_id>/', TestsDeUsuarioPorAdminView.as_view(), name='tests_por_usuario_admin'),
    path('filtro-tecnico/', FiltroPorTecnicoView.as_view(), name='filtro_por_tecnico'), 

    path('', include(router.urls)), 
]
