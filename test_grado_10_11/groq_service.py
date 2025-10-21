# test_grado_10_11/groq_service.py
import json
import requests
from django.conf import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # igual que 9; si quieres: "llama-3.3-70b-versatile"

def generar_explicacion_carrera(carrera, respuestas):
    # Asegura que 'respuestas' sea texto legible (por si es dict/list)
    if not isinstance(respuestas, str):
        try:
            respuestas = json.dumps(respuestas, ensure_ascii=False)
        except Exception:
            respuestas = str(respuestas)

    system_msg = (
        "Eres un orientador vocacional empático. Responde en español, "
        "con tono juvenil, claro y motivador. Sé breve (80–120 palabras) "
        "y evita tecnicismos innecesarios."
    )

    user_prompt = f"""
Eres un orientador vocacional para estudiantes de colegio (grados 10 y 11). 
El modelo ha sugerido la carrera universitaria "{carrera}".

Las respuestas del test (1=No me interesa, 4=Me gusta) fueron:
{respuestas}

Redacta una explicación clara, educativa, breve y motivadora sobre por qué se recomienda esta carrera. 
Usa un lenguaje juvenil y positivo y cierra con un siguiente paso práctico (materias, clubes o proyectos).
""".strip()

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        print("🟡 Groq status:", response.status_code)
        try:
            print("🟡 Groq response body:", response.text[:2000])
        except Exception:
            pass

        if response.status_code == 200:
            payload = response.json()
            return payload["choices"][0]["message"]["content"].strip()

        try:
            err = response.json()
        except Exception:
            err = {"raw": response.text}
        return f"No se pudo generar la explicación (status {response.status_code}): {err}"

    except requests.Timeout:
        return "Error: tiempo de espera agotado al conectar con Groq."
    except Exception as e:
        print("🔴 Error al conectar con Groq:", str(e))
        return f"Error al conectar con Groq: {str(e)}"
