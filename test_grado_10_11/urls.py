from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestGrado10_11ViewSet,ResultadoTest10_11PorIDView,TestsGrado10_11DeUsuarioView, FiltroPorCarreraView

router = DefaultRouter()
router.register(r'', TestGrado10_11ViewSet, basename='testgrado10_11')

urlpatterns = [
    path('resultado/<int:test_id>/', ResultadoTest10_11PorIDView.as_view(), name='resultado_test_10_11'),
    path('usuario/<int:user_id>/', TestsGrado10_11DeUsuarioView.as_view(), name='tests_usuario_test_10_11'),
    path('filtro-carrera/', FiltroPorCarreraView.as_view(), name='filtro_por_carrera'),

    path('', include(router.urls)),
]

