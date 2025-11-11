# test_grado_10_11/ml_model/model_10y11.py
# -*- coding: utf-8 -*-
import os
import joblib
import numpy as np
import pandas as pd


# ========= Rutas base (sin extensión) =========
BASE = os.path.join(os.path.dirname(__file__), "modelo_10y11_rf_60preguntas")


# ========= Cargar modelo =========
MODEL = joblib.load(f"{BASE}.pkl")  # RandomForestClassifier puro


# ========= Cargar y LIMPIAR XCOLS =========
_raw_xcols = pd.read_csv(f"{BASE}_xcols.csv", header=None).iloc[:, 0].tolist()


XCOLS = []
for c in _raw_xcols:
    if pd.isna(c):
        continue
    c = str(c).strip()
    if c == "" or c.lower().startswith("unnamed") or c == "0":
        continue
    XCOLS.append(c)


# Solo permitimos preguntas 1..60 y sumas conocidas
VALID_COLS = [f"pregunta_{i}" for i in range(1, 61)]  # ✅ Cambio 41 -> 61
VALID_COLS += [f"suma_{k}" for k in [
    "Medicina", "Ingeniería", "Administración", "Psicología", "Derecho",
    "Educación", "Sistemas/Software", "Contaduría", "Diseño Gráfico", "Ciencias Naturales"
]]
XCOLS = [c for c in XCOLS if c in VALID_COLS]


# Asegurar tamaño que el modelo espera
if hasattr(MODEL, "n_features_in_"):
    n_exp = int(MODEL.n_features_in_)
    if len(XCOLS) > n_exp:
        # recortar manteniendo el orden del CSV ya limpio
        XCOLS = XCOLS[:n_exp]
    elif len(XCOLS) < n_exp:
        raise ValueError(
            f"XCOLS ({len(XCOLS)}) es menor que las features esperadas por el modelo ({n_exp}). "
            f"Revisa el CSV {BASE}_xcols.csv."
        )


# ========= Cargar mapping id -> nombre (limpieza robusta) =========
_id_to_nombre_series = pd.read_csv(f"{BASE}_id_to_nombre.csv", index_col=0, header=None).iloc[:, 0]
# filtrar claves NaN / inválidas, castear a int
ID_TO_NOMBRE = {}
for k, v in _id_to_nombre_series.items():
    if pd.isna(k) or pd.isna(v):
        continue
    try:
        ID_TO_NOMBRE[int(k)] = str(v)
    except Exception:
        continue


# ========= Bloques de preguntas (para meta-features) =========
# ✅ Actualizado a 6 preguntas por carrera (60 total)
PREGUNTAS_CLAVE_POR_CARRERA = {
    "Medicina": list(range(1, 7)),             # 1-6
    "Ingeniería": list(range(7, 13)),          # 7-12
    "Administración": list(range(13, 19)),     # 13-18
    "Psicología": list(range(19, 25)),         # 19-24
    "Derecho": list(range(25, 31)),            # 25-30
    "Educación": list(range(31, 37)),          # 31-36
    "Sistemas/Software": list(range(37, 43)),  # 37-42
    "Contaduría": list(range(43, 49)),         # 43-48
    "Diseño Gráfico": list(range(49, 55)),     # 49-54
    "Ciencias Naturales": list(range(55, 61)), # 55-60
}


# ========= Normalización de respuestas =========
MAP_ABCPAL = {"A": "Me encanta", "B": "Me interesa", "C": "No me gusta"}
MAP_321 = {"Me encanta": 3, "Me interesa": 2, "No me gusta": 1}
VALIDAS = set(MAP_321.keys())


def _normalizar_lista(respuestas_texto):
    """
    Acepta lista de 60 respuestas (texto o A/B/C) y devuelve
    lista de 60 strings en {'Me encanta','Me interesa','No me gusta'}.
    """
    # ✅ Cambio 40 -> 60
    if not isinstance(respuestas_texto, (list, tuple)) or len(respuestas_texto) != 60:
        raise ValueError("Se esperaban 60 respuestas en orden (1..60).")
    out = []
    for r in respuestas_texto:
        r = str(r).strip()
        r = MAP_ABCPAL.get(r, r)  # convierte A/B/C si vienen así
        if r not in VALIDAS:
            raise ValueError("Usa: Me encanta / Me interesa / No me gusta (o A/B/C).")
        out.append(r)
    return out


def _vectorizar(respuestas_texto):
    """
    Convierte respuestas -> vector np.ndarray shape (1, n_features)
    siguiendo EXACTAMENTE XCOLS del entrenamiento.
    """
    resp = _normalizar_lista(respuestas_texto)
    base = [MAP_321[r] for r in resp]
    # ✅ Cambio range(1,41) -> range(1,61)
    s = pd.Series(base, index=[f"pregunta_{i}" for i in range(1, 61)])


    # Agregar meta-features si el modelo las usa (solo si están en XCOLS)
    for carrera, qs in PREGUNTAS_CLAVE_POR_CARRERA.items():
        col = f"suma_{carrera}"
        if col in XCOLS:
            s[col] = s[[f"pregunta_{i}" for i in qs]].sum()


    # Reordenar exactamente como XCOLS
    s = s.reindex(XCOLS)
    # Validación defensiva
    if s.isna().any():
        faltantes = [c for c, v in s.items() if pd.isna(v)]
        raise ValueError(f"Valores NaN al construir el vector. Columnas: {faltantes}")
    arr = s.to_numpy(dtype=np.float32).reshape(1, -1)
    # Asegurar tamaño correcto
    if hasattr(MODEL, "n_features_in_") and arr.shape[1] != int(MODEL.n_features_in_):
        raise ValueError(
            f"Vector con {arr.shape[1]} features, pero el modelo espera {int(MODEL.n_features_in_)}. "
            f"Revisa XCOLS y las meta-features."
        )
    return arr


def _ids_a_nombres(ids):
    """
    Convierte ids de clase -> nombres de carrera usando ID_TO_NOMBRE.
    Si el modelo trae classes_ no 1..N, usamos ese arreglo.
    """
    nombres = []
    for cid in ids:
        # cid puede venir ya como id (p.ej. 1..N), castear a int por seguridad
        try:
            nombres.append(ID_TO_NOMBRE[int(cid)])
        except Exception:
            # fallback por si el mapeo no está: devolver el id como str
            nombres.append(str(cid))
    return nombres


def predecir_carrera(respuestas_texto, top_k: int = 3):
    """
    Retorna:
    {
        "carrera_predicha": <str>,
        "top3": [(nombre, prob), ...]  # prob en [0,1] redondeada a 4
    }
    """
    X = _vectorizar(respuestas_texto)
    proba = MODEL.predict_proba(X)[0]  # arreglo de probabilidades
    # Índices ordenados por prob. descendente (en el espacio de MODEL.classes_)
    idx_sorted = np.argsort(proba)[::-1]


    # Mapear classes_ del modelo a nombres
    if hasattr(MODEL, "classes_"):
        class_ids = list(MODEL.classes_)  # p.ej. [1,2,3,...,10]
    else:
        # fallback (siempre debería existir en RF)
        class_ids = list(range(1, len(proba) + 1))


    ids_ordenados = [class_ids[i] for i in idx_sorted]
    nombres_ordenados = _ids_a_nombres(ids_ordenados)


    top_k = max(1, min(top_k, len(nombres_ordenados)))
    return {
        "carrera_predicha": nombres_ordenados[0],
        "top3": list(zip(nombres_ordenados[:top_k], proba[idx_sorted[:top_k]].round(4).tolist())),
    }
