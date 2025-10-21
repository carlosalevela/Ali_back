# tests_grado1011/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
import json

# Evita el doble json.loads cuando Postgres ya devuelve dict/list
class PassthroughJSONField(models.JSONField):
    def from_db_value(self, value, expression, connection):
        if value is None or isinstance(value, (dict, list)):
            return value
        if isinstance(value, (bytes, bytearray)):
            try:
                value = value.decode("utf-8", errors="ignore")
            except Exception:
                return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

class TestGrado10_11(models.Model):
    ESTADO_EN_PROGRESO = 'EN_PROGRESO'
    ESTADO_FINALIZADO  = 'FINALIZADO'
    ESTADO_CHOICES = [
        (ESTADO_EN_PROGRESO, 'En progreso'),
        (ESTADO_FINALIZADO,  'Finalizado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    respuestas = PassthroughJSONField(default=dict, blank=True)  # ← sólo cambiamos esto

    resultado = models.TextField(blank=True, null=True)

    # Seguimiento temporal
    fecha_inicio = models.DateTimeField(default=timezone.now, editable=False)
    fecha_ultima_actividad = models.DateTimeField(auto_now=True)
    fecha_realizacion = models.DateTimeField(blank=True, null=True)

    # Progreso
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_EN_PROGRESO)
    ultima_pregunta = models.PositiveSmallIntegerField(default=0)
    respondidas = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        fin = self.fecha_realizacion.isoformat() if self.fecha_realizacion else "en_progreso"
        return f"Test 10/11 de {getattr(self.usuario, 'email', self.usuario_id)} - {fin}"

    @property
    def progreso_pct(self) -> float:
        total = 40  # ajusta si tu test tiene otro total
        if not self.respondidas:
            return 0.0
        return round((self.respondidas / total) * 100, 2)
