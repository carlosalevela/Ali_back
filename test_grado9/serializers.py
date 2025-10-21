from rest_framework import serializers
from .models import TestGrado9
from django.conf import settings

TOTAL_PREGUNTAS = getattr(settings, "GRADO9_TOTAL_PREGUNTAS", 57)

class TestGrado9Serializer(serializers.ModelSerializer):
    usuario_email = serializers.ReadOnlyField(source="usuario.email")
    progreso_pct = serializers.SerializerMethodField()

    class Meta:
        model = TestGrado9
        fields = [
            # 🔹 Campos originales
            "id",
            "usuario",
            "usuario_email",
            "respuestas",
            "resultado",
            "fecha_realizacion",

            # 🔹 Progreso/seguimiento
            "estado",
            "ultima_pregunta",
            "respondidas",
            "progreso_pct",
            "fecha_inicio",
            "fecha_ultima_actividad",
        ]
        read_only_fields = [
            "usuario",             # ← Protege la propiedad del test
            "resultado",
            "fecha_realizacion",
            "progreso_pct",
            "fecha_inicio",
            "fecha_ultima_actividad",
            "respondidas",
        ]

    def get_progreso_pct(self, obj: TestGrado9):
        try:
            return getattr(obj, "progreso_pct", None) or round((obj.respondidas / TOTAL_PREGUNTAS) * 100, 2)
        except Exception:
            return 0.0
