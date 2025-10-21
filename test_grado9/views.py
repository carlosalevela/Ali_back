# test_grado9/views.py
import os
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied  # ← ADD

from .models import TestGrado9
from .serializers import TestGrado9Serializer
from .groq_service import generar_explicacion_modalidad

# ⬇️ Modelo nuevo (57 preguntas + metas)
from .ml_model.model9 import predecir as predecir_tecnico

# ----------------- 🔧 Constantes / utilidades -----------------
TOTAL_PREGUNTAS = 57
RESP_VALIDAS = {"Me encanta", "Me interesa", "No me gusta"}   # nuevas opciones
# Compat con front viejo (A/B/C)
MAP_A_B_C = {"A": "Me encanta", "B": "Me interesa", "C": "No me gusta", "D": None}

# Para derivar modalidad desde el técnico (para tu explicación Groq)
MODALIDAD_POR_TECNICO = {
    "Mantenimiento de Hardware y Software": "Industrial",
    "Robótica": "Industrial",
    "Electricidad y Electrónica": "Industrial",
    "Emprendimiento y Fomento Empresarial": "Comercio",
    "Diseño Gráfico": "Comercio",
    "Contabilidad y Finanzas": "Comercio",
    "Primera Infancia": "Promoción Social",
    "Seguridad y Salud en el Trabajo": "Promoción Social",
    "Promoción de la Salud": "Promoción Social",
    "Agroindustria": "Agropecuaria",
    "Científico/Humanista": "Académico",
}

def _contar_respondidas(respuestas: dict) -> int:
    if not isinstance(respuestas, dict):
        return 0
    c = 0
    for i in range(1, TOTAL_PREGUNTAS + 1):
        r = respuestas.get(f"pregunta_{i}")
        if r is None:
            continue
        r = str(r).strip()
        if r in RESP_VALIDAS or (r in MAP_A_B_C and MAP_A_B_C[r] in RESP_VALIDAS):
            c += 1
    return c

def _ultima_pregunta(respuestas: dict) -> int:
    if not isinstance(respuestas, dict):
        return 0
    last = 0
    for i in range(1, TOTAL_PREGUNTAS + 1):
        r = respuestas.get(f"pregunta_{i}")
        if r is None:
            continue
        r = str(r).strip()
        if r in RESP_VALIDAS or (r in MAP_A_B_C and MAP_A_B_C[r] in RESP_VALIDAS):
            last = i
    return last

def _normalizar_respuestas(respuestas_dict: dict):
    """
    Devuelve lista de 57 strings (Me encanta/Me interesa/No me gusta) en orden.
    Si falta alguna o hay inválidas -> None.
    """
    if not isinstance(respuestas_dict, dict):
        return None
    out = []
    for i in range(1, TOTAL_PREGUNTAS + 1):
        r = respuestas_dict.get(f"pregunta_{i}")
        if r is None:
            return None
        r = str(r).strip()
        if r in MAP_A_B_C:  # acepta A/B/C también
            r = MAP_A_B_C[r]
        if r not in RESP_VALIDAS:
            return None
        out.append(r)
    return out

def _finalizar_y_predecir(test_instance: TestGrado9):
    """
    Finaliza el test y predice con el nuevo modelo (57 preguntas, 3 opciones).
    - Salida principal: técnico_predicho
    - Además derivamos modalidad (para Groq).
    """
    respuestas = test_instance.respuestas or {}

    respuestas_norm = _normalizar_respuestas(respuestas)
    if respuestas_norm is None:
        return  # aún no finaliza (faltan o inválidas)

    # Predicción con el modelo nuevo (top_k=3)
    pred = predecir_tecnico(respuestas_norm, top_k=3)
    tecnico = pred.get("tecnico_predicho")
    # soportar 'top3' o 'topk' según implementación
    top3 = pred.get("top3") or pred.get("topk") or []
    modalidad = MODALIDAD_POR_TECNICO.get(tecnico, "Desconocido")

    # Si tu prompt de Groq espera valores 3/2/1:
    mapeo_321 = {"Me encanta": 3, "Me interesa": 2, "No me gusta": 1}
    respuestas_codificadas = {f"pregunta_{i}": mapeo_321[r] for i, r in enumerate(respuestas_norm, start=1)}

    # Explicación con fallback
    try:
        explicacion = generar_explicacion_modalidad(modalidad, respuestas_codificadas)
    except Exception:
        explicacion = "No fue posible generar la explicación automática en este momento."

    detalle_top3 = ", ".join([f"{nombre} ({float(prob):.2f})" for nombre, prob in top3])
    resultado_completo = (
        f"Técnico sugerido por ALI: {tecnico}\n"
        f"Modalidad asociada: {modalidad}\n"
        f"Top-3: {detalle_top3}\n\n"
        f"Explicación: {explicacion}"
    )

    # Marcar finalizado
    test_instance.resultado = resultado_completo
    test_instance.estado = TestGrado9.ESTADO_FINALIZADO
    test_instance.fecha_realizacion = timezone.now()
    test_instance.save(update_fields=['resultado', 'estado', 'fecha_realizacion', 'fecha_ultima_actividad'])

# ================== ViewSet principal ==================
class TestGrado9ViewSet(viewsets.ModelViewSet):
    serializer_class = TestGrado9Serializer
    permission_classes = [IsAuthenticated]

    # ← ADD: refuerza propiedad para TODAS las acciones detail (retrieve/update/partial_update/destroy)
    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if not (user.is_staff or user.is_superuser or obj.usuario_id == user.id):
            raise PermissionDenied("No tienes permiso para ver o modificar este test.")
        return obj

    def get_queryset(self):
        user = self.request.user
        qs = TestGrado9.objects.all()

        if user.is_staff or user.is_superuser:
            estado = self.request.query_params.get('estado')
            if estado in (TestGrado9.ESTADO_EN_PROGRESO, TestGrado9.ESTADO_FINALIZADO):
                qs = qs.filter(estado=estado)

            orden = self.request.query_params.get('orden')
            if orden == 'actividad':
                return qs.order_by('-fecha_ultima_actividad', '-id')

            return qs.order_by('-fecha_realizacion', '-id')

        return TestGrado9.objects.filter(usuario=user).order_by('-fecha_realizacion', '-id')

    def perform_create(self, serializer):
        """
        Guarda el test con el usuario autenticado.
        - Si llegan 57/57 válidas => finaliza + predice + explicación.
        - Si vienen parciales => EN_PROGRESO y actualiza progreso.
        """
        test_instance = serializer.save(usuario=self.request.user)

        # ← ADD: asegura fecha_inicio
        if not test_instance.fecha_inicio:
            test_instance.fecha_inicio = timezone.now()
            test_instance.save(update_fields=['fecha_inicio'])

        respuestas = test_instance.respuestas or {}

        test_instance.respondidas = _contar_respondidas(respuestas)
        test_instance.ultima_pregunta = _ultima_pregunta(respuestas)

        try:
            if test_instance.respondidas < TOTAL_PREGUNTAS:
                test_instance.estado = TestGrado9.ESTADO_EN_PROGRESO
                test_instance.save(update_fields=['respondidas', 'ultima_pregunta', 'estado'])
                return  # no predice aún

            # Validación final (todas presentes y válidas)
            if _normalizar_respuestas(respuestas) is None:
                test_instance.resultado = (
                    "Error: respuestas inválidas. Usa Me encanta / Me interesa / No me gusta (o A/B/C)."
                )
                test_instance.estado = TestGrado9.ESTADO_EN_PROGRESO
                test_instance.save(update_fields=['resultado', 'estado', 'respondidas', 'ultima_pregunta'])
                return

            _finalizar_y_predecir(test_instance)

        except Exception as e:
            test_instance.resultado = f"Error interno: {str(e)}"
            test_instance.save(update_fields=['resultado'])

    # ---------- Acciones para progreso en vivo ----------
    @action(detail=False, methods=['post'], url_path='iniciar')
    def iniciar(self, request):
        user = request.user
        draft = (TestGrado9.objects
                 .filter(usuario=user, estado=TestGrado9.ESTADO_EN_PROGRESO)
                 .order_by('-fecha_ultima_actividad')
                 .first())
        if not draft:
            draft = TestGrado9.objects.create(
                usuario=user,
                respuestas={},
                fecha_inicio=timezone.now()  # ← ADD: fecha de inicio al crear borrador
            )
        return Response(TestGrado9Serializer(draft).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='progreso')
    def progreso(self, request, pk=None):
        user = request.user
        try:
            test = TestGrado9.objects.get(pk=pk)
        except TestGrado9.DoesNotExist:
            return Response({"error": "Test no existe."}, status=status.HTTP_404_NOT_FOUND)

        if not (user.is_staff or user.is_superuser or test.usuario_id == user.id):
            return Response({"error": "No tienes permiso para modificar este test."},
                            status=status.HTTP_403_FORBIDDEN)

        if test.estado == TestGrado9.ESTADO_FINALIZADO:
            return Response({"error": "El test ya está finalizado."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        respuestas = dict(test.respuestas or {})
        updates = {}

        # Carga simple
        if 'pregunta' in data and 'respuesta' in data:
            try:
                n = int(data['pregunta'])
            except Exception:
                return Response({"error": "Índice de pregunta inválido."}, status=400)
            r = str(data['respuesta']).strip()
            if not (1 <= n <= TOTAL_PREGUNTAS):
                return Response({"error": f"Índice de pregunta fuera de 1..{TOTAL_PREGUNTAS}."}, status=400)
            # aceptar A/B/C además de texto
            if r not in RESP_VALIDAS and not (r in MAP_A_B_C and MAP_A_B_C[r] in RESP_VALIDAS):
                return Response(
                    {"error": "Respuesta inválida (Me encanta / Me interesa / No me gusta o A/B/C)."},
                    status=400
                )
            updates[f"pregunta_{n}"] = r

        # Carga múltiple
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
                if r in RESP_VALIDAS or (r in MAP_A_B_C and MAP_A_B_C[r] in RESP_VALIDAS):
                    updates[f"pregunta_{idx}"] = r
                else:
                    return Response(
                        {"error": f"Inválida {k} (Me encanta / Me interesa / No me gusta o A/B/C)."},
                        status=400
                    )

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

            # estado según completitud
            if test.respondidas >= TOTAL_PREGUNTAS:
                test.estado = TestGrado9.ESTADO_FINALIZADO
            else:
                test.estado = TestGrado9.ESTADO_EN_PROGRESO

            test.save()

        # Si se completó aquí, finaliza y predice
        if test.estado == TestGrado9.ESTADO_FINALIZADO:
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
class ResultadoTest9PorIDView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, test_id):
        user = self.request.user
        try:
            if user.is_staff or user.is_superuser:
                test = TestGrado9.objects.get(id=test_id)
            else:
                test = TestGrado9.objects.get(id=test_id, usuario=user)
        except TestGrado9.DoesNotExist:
            return Response({"error": "No tienes acceso a este test o no existe."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TestGrado9Serializer(test)
        return Response(serializer.data)

class TestsDeUsuarioPorAdminView(APIView):
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

        tests = TestGrado9.objects.filter(usuario=usuario).order_by('-fecha_realizacion')
        serializer = TestGrado9Serializer(tests, many=True)
        return Response(serializer.data)

class FiltroPorTecnicoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_staff or user.is_superuser):
            return Response({"error": "No tienes permisos para ver esta información."},
                            status=status.HTTP_403_FORBIDDEN)

        tecnico = request.query_params.get("tecnico", "").strip()
        if not tecnico:
            return Response({"error": "Debes especificar un técnico en el parámetro 'tecnico'."},
                            status=status.HTTP_400_BAD_REQUEST)

        tests_filtrados = TestGrado9.objects.filter(resultado__icontains=tecnico).order_by("-fecha_realizacion")
        serializer = TestGrado9Serializer(tests_filtrados, many=True)
        return Response(serializer.data)
