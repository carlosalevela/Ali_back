# test_grado_10_11/views.py
import numpy as np
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView

from .models import TestGrado10_11
from .serializers import TestGrado10_11Serializer
from .groq_service import generar_explicacion_carrera
from .ml_model.model_10y11 import predecir_carrera  # 👈 usa el loader nuevo

# ----------------- Config / utilidades -----------------
TOTAL_PREGUNTAS = 40

# Aceptamos texto o A/B/C
VALID_TEXT = {"Me encanta", "Me interesa", "No me gusta"}
MAP_A_B_C = {"A": "Me encanta", "B": "Me interesa", "C": "No me gusta"}  # D ya no existe
MAP_321 = {"Me encanta": 3, "Me interesa": 2, "No me gusta": 1}

def _is_valida(r):
    r = (r or "").strip()
    return (r in VALID_TEXT) or (r in MAP_A_B_C and MAP_A_B_C[r] in VALID_TEXT)

def _normalizar_respuestas(respuestas_dict):
    """Devuelve lista de 40 en formato texto ('Me encanta'/'Me interesa'/'No me gusta')
       o None si faltan/son inválidas."""
    if not isinstance(respuestas_dict, dict):
        return None
    out = []
    for i in range(1, TOTAL_PREGUNTAS + 1):
        r = str(respuestas_dict.get(f"pregunta_{i}", "")).strip()
        if not _is_valida(r):
            return None
        out.append(MAP_A_B_C.get(r, r))  # si viene A/B/C -> texto
    return out

def _contar_respondidas(respuestas: dict) -> int:
    if not isinstance(respuestas, dict):
        return 0
    return sum(1 for i in range(1, TOTAL_PREGUNTAS + 1)
               if _is_valida(respuestas.get(f"pregunta_{i}", "")))

def _ultima_pregunta(respuestas: dict) -> int:
    if not isinstance(respuestas, dict):
        return 0
    last = 0
    for i in range(1, TOTAL_PREGUNTAS + 1):
        if _is_valida(respuestas.get(f"pregunta_{i}", "")):
            last = i
    return last

def _finalizar_y_predecir(test_instance: TestGrado10_11):
    """Predice carrera con el nuevo modelo y genera explicación."""
    respuestas = test_instance.respuestas or {}
    respuestas_norm = _normalizar_respuestas(respuestas)
    if respuestas_norm is None:
        return  # aún no está completo/válido

    # Predicción
    pred = predecir_carrera(respuestas_norm, top_k=3)
    carrera = pred["carrera_predicha"]
    top3 = pred["top3"]  # [(nombre, prob), ...]

    # Codificado 3/2/1 para tu prompt de Groq
    respuestas_codificadas = {f"pregunta_{i}": MAP_321[r]
                              for i, r in enumerate(respuestas_norm, start=1)}
    explicacion = generar_explicacion_carrera(carrera, respuestas_codificadas)

    detalle_top3 = ", ".join([f"{n} ({p:.2f})" for n, p in top3])
    resultado = (
        f"Carrera sugerida por ALI: {carrera}\n"
        f"Top-3: {detalle_top3}\n\n"
        f"Explicación: {explicacion}"
    )

    test_instance.resultado = resultado
    test_instance.estado = TestGrado10_11.ESTADO_FINALIZADO
    if not test_instance.fecha_realizacion:
        test_instance.fecha_realizacion = timezone.now()
    test_instance.save(update_fields=['resultado', 'estado', 'fecha_realizacion', 'fecha_ultima_actividad'])

# ================== ViewSet principal ==================
class TestGrado10_11ViewSet(viewsets.ModelViewSet):
    serializer_class = TestGrado10_11Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = TestGrado10_11.objects.all()

        if user.is_staff or user.is_superuser:
            estado = self.request.query_params.get('estado')
            if estado in (TestGrado10_11.ESTADO_EN_PROGRESO, TestGrado10_11.ESTADO_FINALIZADO):
                qs = qs.filter(estado=estado)

            orden = self.request.query_params.get('orden')
            if orden == 'actividad':
                return qs.order_by('-fecha_ultima_actividad', '-id')

            return qs.order_by('-fecha_realizacion', '-id')

        return TestGrado10_11.objects.filter(usuario=user).order_by('-fecha_realizacion', '-id')

    def perform_create(self, serializer):
        test_instance = serializer.save(usuario=self.request.user)
        respuestas = test_instance.respuestas or {}

        test_instance.respondidas = _contar_respondidas(respuestas)
        test_instance.ultima_pregunta = _ultima_pregunta(respuestas)

        try:
            if test_instance.respondidas < TOTAL_PREGUNTAS:
                test_instance.estado = TestGrado10_11.ESTADO_EN_PROGRESO
                test_instance.save(update_fields=['respondidas', 'ultima_pregunta', 'estado'])
                return

            if _normalizar_respuestas(respuestas) is None:
                test_instance.resultado = "Error: respuestas inválidas. Usa Me encanta / Me interesa / No me gusta (o A/B/C)."
                test_instance.estado = TestGrado10_11.ESTADO_EN_PROGRESO
                test_instance.save(update_fields=['resultado', 'estado', 'respondidas', 'ultima_pregunta'])
                return

            _finalizar_y_predecir(test_instance)

        except Exception as e:
            test_instance.resultado = f"Error interno: {str(e)}"
            test_instance.save(update_fields=['resultado'])

    @action(detail=False, methods=['post'], url_path='iniciar')
    def iniciar(self, request):
        user = request.user
        draft = (TestGrado10_11.objects
                 .filter(usuario=user, estado=TestGrado10_11.ESTADO_EN_PROGRESO)
                 .order_by('-fecha_ultima_actividad')
                 .first())
        if not draft:
            draft = TestGrado10_11.objects.create(usuario=user, respuestas={})
        return Response(TestGrado10_11Serializer(draft).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='progreso')
    def progreso(self, request, pk=None):
        user = request.user
        try:
            test = TestGrado10_11.objects.get(pk=pk)
        except TestGrado10_11.DoesNotExist:
            return Response({"error": "Test no existe."}, status=status.HTTP_404_NOT_FOUND)

        if not (user.is_staff or user.is_superuser or test.usuario_id == user.id):
            return Response({"error": "No tienes permiso para modificar este test."},
                            status=status.HTTP_403_FORBIDDEN)

        if test.estado == TestGrado10_11.ESTADO_FINALIZADO:
            return Response({"error": "El test ya está finalizado."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        respuestas = dict(test.respuestas or {})
        updates = {}

        # Un único item
        if 'pregunta' in data and 'respuesta' in data:
            try:
                n = int(data['pregunta'])
            except Exception:
                return Response({"error": "Índice de pregunta inválido."}, status=400)
            r = str(data['respuesta']).strip()
            if not (1 <= n <= TOTAL_PREGUNTAS):
                return Response({"error": f"Índice de pregunta fuera de 1..{TOTAL_PREGUNTAS}."}, status=400)
            if not _is_valida(r):
                return Response({"error": "Respuesta inválida (Me encanta / Me interesa / No me gusta o A/B/C)."}, status=400)
            updates[f"pregunta_{n}"] = r

        # Varios items
        if 'respuestas' in data and isinstance(data['respuestas'], dict):
            for k, v in data['respuestas'].items():
                if not k.startswith('pregunta_'):
                    continue
                try:
                    idx = int(k.split('_')[1])
                except Exception:
                    continue
                r = str(v).strip()
                if not (1 <= idx <= TOTAL_PREGUNTAS):
                    return Response({"error": f"Índice de pregunta fuera de 1..{TOTAL_PREGUNTAS}."}, status=400)
                if not _is_valida(r):
                    return Response({"error": f"Inválida {k} (Me encanta / Me interesa / No me gusta o A/B/C)."}, status=400)
                updates[f"pregunta_{idx}"] = r

        if not updates:
            return Response({"error": "No hay respuestas válidas para actualizar."}, status=400)

        with transaction.atomic():
            respuestas.update(updates)
            test.respuestas = respuestas
            test.respondidas = _contar_respondidas(respuestas)
            up_exp = data.get('ultima_pregunta')
            if isinstance(up_exp, int) and 1 <= up_exp <= TOTAL_PREGUNTAS:
                test.ultima_pregunta = up_exp
            else:
                test.ultima_pregunta = _ultima_pregunta(respuestas)

            if test.respondidas >= TOTAL_PREGUNTAS:
                test.estado = TestGrado10_11.ESTADO_FINALIZADO
                if not test.fecha_realizacion:
                    test.fecha_realizacion = timezone.now()
            else:
                test.estado = TestGrado10_11.ESTADO_EN_PROGRESO

            test.save()

        if test.estado == TestGrado10_11.ESTADO_FINALIZADO:
            try:
                _finalizar_y_predecir(test)
            except Exception as e:
                test.resultado = f"Error interno: {str(e)}"
                test.save(update_fields=['resultado'])

        return Response({
            "id": test.id,
            "estado": test.estado,
            "respondidas": test.respondidas,
            "total": TOTAL_PREGUNTAS,
            "progreso_pct": round((test.respondidas / TOTAL_PREGUNTAS) * 100, 2),
            "ultima_pregunta": test.ultima_pregunta,
            "fecha_ultima_actividad": test.fecha_ultima_actividad,
        }, status=200)

# ----------------- APIViews existentes -----------------
class ResultadoTest10_11PorIDView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, test_id):
        user = request.user
        try:
            if user.is_staff or user.is_superuser:
                test = TestGrado10_11.objects.get(id=test_id)
            else:
                test = TestGrado10_11.objects.get(id=test_id, usuario=user)
        except TestGrado10_11.DoesNotExist:
            return Response({"error": "No tienes acceso a este test o no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = TestGrado10_11Serializer(test)
        return Response(serializer.data)

class TestsGrado10_11DeUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "No tienes permiso para ver esta información."},
                            status=status.HTTP_403_FORBIDDEN)

        User = get_user_model()
        try:
            usuario = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "El usuario no existe."}, status=status.HTTP_404_NOT_FOUND)

        tests = TestGrado10_11.objects.filter(usuario=usuario).order_by('-fecha_realizacion')
        serializer = TestGrado10_11Serializer(tests, many=True)
        return Response(serializer.data)

class FiltroPorCarreraView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"error": "No tienes permisos para ver esta información."},
                            status=status.HTTP_403_FORBIDDEN)

        carrera = request.query_params.get("carrera", "").strip()
        if not carrera:
            return Response({"error": "Debes especificar una carrera en el parámetro 'carrera'."},
                            status=status.HTTP_400_BAD_REQUEST)

        tests_filtrados = (TestGrado10_11.objects
                           .filter(resultado__icontains=carrera)
                           .order_by("-fecha_realizacion"))
        serializer = TestGrado10_11Serializer(tests_filtrados, many=True)
        return Response(serializer.data)
