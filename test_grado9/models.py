from django.db import models
from django.conf import settings
from django.utils import timezone
import json

# Campo JSON tolerante: si ya viene dict/list desde Postgres, no lo vuelve a cargar.
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

class TestGrado9(models.Model):
    ESTADO_EN_PROGRESO = 'EN_PROGRESO'
    ESTADO_FINALIZADO  = 'FINALIZADO'
    ESTADO_CHOICES = [
        (ESTADO_EN_PROGRESO, 'En progreso'),
        (ESTADO_FINALIZADO,  'Finalizado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Puede almacenar respuestas parciales (tolerante a dict/str)
    respuestas = PassthroughJSONField(default=dict, blank=True)

    # Resultado final (solo cuando está completo)
    resultado = models.TextField(blank=True, null=True)

    # 🔄 Nuevo: fechas para seguimiento
    fecha_inicio = models.DateTimeField(null=True, blank=True)       # cuándo se creó/inició
    fecha_ultima_actividad = models.DateTimeField(auto_now=True)     # se actualiza en cada guardado
    fecha_realizacion = models.DateTimeField(blank=True, null=True)  # ✅ ahora es “cuando finaliza”

    # 🔄 Nuevos: progreso
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ESTADO_EN_PROGRESO)
    ultima_pregunta = models.PositiveSmallIntegerField(default=0)  # 0..40
    respondidas = models.PositiveSmallIntegerField(default=0)       # 0..40

    def __str__(self):
        fin = self.fecha_realizacion.isoformat() if self.fecha_realizacion else "en_progreso"
        return f"Test de {getattr(self.usuario, 'email', self.usuario_id)} - {fin}"

    @property
    def progreso_pct(self) -> float:
        total = 57
        return round((self.respondidas / total) * 100, 2)
