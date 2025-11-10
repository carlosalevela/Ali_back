from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TestGrado9ViewSet,
    ResultadoTest9PorIDView,
    TestsDeUsuarioPorAdminView,
    FiltroPorTecnicoView,
    TestGrado9Top3CreateView,
    TestGrado9Top3ListAdminView,
)

router = DefaultRouter()
router.register(r'', TestGrado9ViewSet, basename='test_grado9')

urlpatterns = [
    path('resultado/<int:test_id>/', ResultadoTest9PorIDView.as_view(), name='resultado_test_9'),
    path('usuario/<int:user_id>/', TestsDeUsuarioPorAdminView.as_view(), name='tests_por_usuario_admin'),
    path('filtro-tecnico/', FiltroPorTecnicoView.as_view(), name='filtro_por_tecnico'),

    # 👇 NUEVOS endpoints para el Top 3 (pregunta inicial)
    path('top3/', TestGrado9Top3CreateView.as_view(), name='tests_grado9_top3_create'),
    path('top3/list/', TestGrado9Top3ListAdminView.as_view(), name='tests_grado9_top3_list'),

    path('', include(router.urls)),
]
