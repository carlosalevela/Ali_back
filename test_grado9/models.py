from django.db import models
from django.conf import settings
from django.utils import timezone
import json
# 👇 NUEVO: para ArrayField (PostgreSQL)
from django.contrib.postgres.fields import ArrayField

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


# ================================
# NUEVO: Tabla para la pregunta inicial (Top 3)
# ================================
class TestGrado9Top3(models.Model):
    """
    Guarda exclusivamente la pregunta inicial de selección múltiple (Top 3)
    sin afectar el scoring del TestGrado9.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='grado9_top3'
    )
    # exactamente 3 selecciones (catálogo controlado desde serializer)
    selecciones = ArrayField(models.CharField(max_length=80), size=3)

    # opcional: referenciar un TestGrado9 específico si se desea asociar el top3 a un intento concreto
    test = models.ForeignKey(
        TestGrado9,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='top3_inicial'
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Top 3 inicial (Grado 9)'
        verbose_name_plural = 'Top 3 inicial (Grado 9)'
        ordering = ['-creado_en']

    def __str__(self):
        try:
            return f'Top3 {self.usuario_id}: {", ".join(self.selecciones or [])}'
        except Exception:
            return f'Top3 {self.usuario_id}'
