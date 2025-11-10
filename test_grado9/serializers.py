from rest_framework import serializers
from .models import TestGrado9, TestGrado9Top3
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


# ================================
# NUEVO: Serializer para Top 3 inicial
# ================================
ALLOWED_MODALIDADES = {
    'Emprendimiento y Fomento Empresarial',
    'Diseño Gráfico',
    'Contabilidad y Finanzas',
    'Mantenimiento de Hardware y Software',
    'Electricidad y Electrónica',
    'Robótica',
    'Agroindustria',
    'Academico',
    'Primera Infancia',
    'Seguridad y Salud en el Trabajo',
    'Promoción de la Salud',
}

class TestGrado9Top3Serializer(serializers.ModelSerializer):
    # usuario se toma del request en create()
    selecciones = serializers.ListField(
        child=serializers.CharField(max_length=80),
        allow_empty=False
    )
    test = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True, queryset=TestGrado9.objects.all()
    )

    class Meta:
        model = TestGrado9Top3
        fields = ["id", "usuario", "selecciones", "test", "creado_en"]
        read_only_fields = ["id", "usuario", "creado_en"]

    def validate_selecciones(self, value):
        if len(value) != 3:
            raise serializers.ValidationError("Debes enviar exactamente 3 selecciones.")
        if len(set(value)) != 3:
            raise serializers.ValidationError("No se permiten selecciones repetidas.")
        invalid = [v for v in value if v not in ALLOWED_MODALIDADES]
        if invalid:
            raise serializers.ValidationError(f"Selecciones inválidas: {', '.join(invalid)}.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['usuario'] = request.user
        return super().create(validated_data)
