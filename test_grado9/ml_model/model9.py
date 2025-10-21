# test_grado9/ml_model/model9.py
# -*- coding: utf-8 -*-
"""
Inferencia para el test de 9° con 57 preguntas (A/B/C -> 3/2/1) + meta-features.
Requiere los artefactos entrenados:
- modelo_tecnico_mejor_57.joblib
- modelo_tecnico_mejor_57_xcols_fixed.csv   (57 preguntas + 11 metas = 68 cols)
- modelo_tecnico_mejor_57_tecnicos_orden.csv
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

# ========= Rutas =========
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "modelo_tecnico_mejor_57.joblib")
XCOLS_PATH = os.path.join(BASE_DIR, "modelo_tecnico_mejor_57_xcols_fixed.csv")
TECS_PATH  = os.path.join(BASE_DIR, "modelo_tecnico_mejor_57_tecnicos_orden.csv")
# (opcional) por si guardaste bloques/metadata
BLOQUES_JSON = os.path.join(BASE_DIR, "modelo_tecnico_mejor_57_bloques.json")

# ========= Definiciones del test =========
TOTAL_PREGUNTAS = 57

PREGUNTAS_POR_TECNICO = {
    # Comercio (1–15)
    "Emprendimiento y Fomento Empresarial": list(range(1, 6)),     # 1–5
    "Diseño Gráfico": list(range(6, 11)),                           # 6–10
    "Contabilidad y Finanzas": list(range(11, 16)),                 # 11–15

    # Industrial (16–30)
    "Mantenimiento de Hardware y Software": list(range(16, 21)),    # 16–20
    "Electricidad y Electrónica": list(range(21, 26)),              # 21–25
    "Robótica": list(range(26, 31)),                                # 26–30

    # Promoción Social (31–45)
    "Primera Infancia": list(range(31, 36)),                        # 31–35
    "Seguridad y Salud en el Trabajo": list(range(36, 41)),         # 36–40
    "Promoción de la Salud": list(range(41, 46)),                   # 41–45

    # Agropecuaria (46–51)
    "Agroindustria": list(range(46, 52)),                           # 46–51

    # Académico (52–57)
    "Científico/Humanista": list(range(52, 58)),                    # 52–57
}

MAP_ABCB = {"A": "Me encanta", "B": "Me interesa", "C": "No me gusta"}
SCORE = {"Me encanta": 3, "Me interesa": 2, "No me gusta": 1}
VALIDS = set(SCORE.keys())

# ========= Carga de artefactos =========
MODEL = joblib.load(MODEL_PATH)
XCOLS = pd.read_csv(XCOLS_PATH, header=None).iloc[:, 0].astype(str).tolist()
try:
    TECNICOS_ORDEN = pd.read_csv(TECS_PATH, header=None).iloc[:, 0].astype(str).tolist()
except Exception:
    # Fallback: si no existe, intenta usar las clases del modelo si ya vienen legibles
    try:
        TECNICOS_ORDEN = list(MODEL.classes_)
        # Asegura strings
        TECNICOS_ORDEN = [str(x) for x in TECNICOS_ORDEN]
    except Exception:
        TECNICOS_ORDEN = []

# ========= Utilidades =========
def _normalizar_respuestas(resps):
    """
    Acepta 57 respuestas en:
      - texto: 'Me encanta' / 'Me interesa' / 'No me gusta'
      - letras: A/B/C
    Devuelve lista estandarizada de 57 textos válidos (en el orden 1..57).
    """
    if not isinstance(resps, (list, tuple)) or len(resps) != TOTAL_PREGUNTAS:
        raise ValueError(f"Se esperaban {TOTAL_PREGUNTAS} respuestas en orden (1..{TOTAL_PREGUNTAS}).")

    out = []
    for r in resps:
        r = str(r).strip()
        r = MAP_ABCB.get(r.upper(), r)  # convierte A/B/C si llega así
        if r not in VALIDS:
            raise ValueError("Respuestas válidas: Me encanta / Me interesa / No me gusta (o A/B/C).")
        out.append(r)
    return out


def _vectorizar(respuestas_texto):
    """
    Construye el vector de entrada exactamente con el orden de XCOLS:
      - 'pregunta_1'..'pregunta_57'
      - meta-features 'suma_<tecnico>' que estén presentes en XCOLS
    """
    resps = _normalizar_respuestas(respuestas_texto)
    base_vals = [SCORE[r] for r in resps]
    s = pd.Series(base_vals, index=[f"pregunta_{i}" for i in range(1, TOTAL_PREGUNTAS + 1)])

    # Meta-features si el modelo las espera
    for tecnico, qs in PREGUNTAS_POR_TECNICO.items():
        col = f"suma_{tecnico}"
        if col in XCOLS:
            s[col] = s[[f"pregunta_{q}" for q in qs]].sum()

    # Orden EXACTO como XCOLS (usa el CSV *_xcols_fixed.csv)
    s = s.reindex(XCOLS)
    return s.to_numpy(dtype=np.float32).reshape(1, -1)


def predecir(respuestas_texto, top_k: int = 3):
    """
    Predice el técnico y devuelve top-k.
    Retorno:
    {
      "tecnico_predicho": <str>,
      "topk": [(tecnico, prob), ...]   # probs en [0,1]
    }
    """
    X = _vectorizar(respuestas_texto)
    proba = MODEL.predict_proba(X)[0]
    idx = np.argsort(proba)[::-1]

    # Mapear índices a nombres de técnico (según orden de entrenamiento)
    if TECNICOS_ORDEN and len(TECNICOS_ORDEN) == len(proba):
        tecs = [TECNICOS_ORDEN[i] for i in idx]
    else:
        # fallback sin CSV de clases
        tecs = [f"Clase_{i}" for i in idx]

    top_k = max(1, min(top_k, len(tecs)))
    return {
        "tecnico_predicho": tecs[0],
        "topk": list(zip(tecs[:top_k], proba[idx[:top_k]].round(4).tolist()))
    }


# ========= Script rápido de prueba =========
if __name__ == "__main__":
    # Perfil que favorece Robótica (26–30 altas)
    fav = set(PREGUNTAS_POR_TECNICO["Robótica"])
    demo = ["Me encanta" if i in fav else "No me gusta" for i in range(1, TOTAL_PREGUNTAS + 1)]
    print(predecir(demo, top_k=3))
