from rest_framework import serializers
from .models import TestGrado10_11

class TestGrado10_11Serializer(serializers.ModelSerializer):
    usuario_email = serializers.ReadOnlyField(source='usuario.email')
    progreso_pct = serializers.SerializerMethodField()

    class Meta:
        model = TestGrado10_11
        fields = [
            # ✅ Tus campos originales (intactos)
            'id', 'usuario', 'usuario_email', 'respuestas', 'resultado', 'fecha_realizacion',

            # ✅ Nuevos campos de progreso/seguimiento (solo lectura)
            'estado', 'ultima_pregunta', 'respondidas', 'progreso_pct',
            'fecha_inicio', 'fecha_ultima_actividad',
        ]
        read_only_fields = [
            'id', 'usuario_email', 'fecha_realizacion', 'resultado',
            'respondidas', 'progreso_pct', 'fecha_inicio', 'fecha_ultima_actividad', 'estado', 'ultima_pregunta'
        ]

    def get_progreso_pct(self, obj: TestGrado10_11) -> float:
        try:
            # Si el modelo tiene @property progreso_pct lo usamos; si no, lo calculamos aquí.
            return getattr(obj, 'progreso_pct', None) or round((obj.respondidas / 40) * 100, 2)
        except Exception:
            return 0.0
