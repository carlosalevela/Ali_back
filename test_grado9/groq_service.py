import json
import requests
from django.conf import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # Alternativa de más calidad: "llama-3.3-70b-versatile"

def generar_explicacion_modalidad(modalidad, respuestas):
    # Asegura que 'respuestas' sea texto legible (por si es dict/list)
    if not isinstance(respuestas, str):
        try:
            respuestas = json.dumps(respuestas, ensure_ascii=False)
        except Exception:
            respuestas = str(respuestas)

    # === SOLO CAMBIA ESTE BLOQUE: system_msg y user_prompt ===
    system_msg = (
        "Eres un orientador vocacional empático y claro. Responde SIEMPRE en español de Colombia, "
        "con tono juvenil, respetuoso y motivador. Extensión objetivo: 90–130 palabras. "
        "Estructura obligatoria en 3 partes con títulos: "
        "1) Por qué encaja, 2) Qué aprenderá/hará allí, 3) Siguientes pasos. "
        "No uses tecnicismos innecesarios; evita promesas de empleo garantizado o salarios. "
        "Sé específico y conecta con intereses del/la estudiante según sus respuestas. "
        "Si algo no aplica, omítelo sin inventar. Cierra con una invitación breve a explorar más."
    )

    user_prompt = f'''
Contexto del proyecto:
Estudiantes de grado 9 del INEM responden un test (escala 1–4: 1=No me interesa, 4=Me gusta). 
El sistema sugiere una modalidad técnica llamada: "{modalidad}". 
Debes justificarla usando ÚNICAMENTE el perfil de egresado de esa modalidad/especialidad y las respuestas del test.

Instrucciones de interpretación de respuestas:
- Identifica patrones (p. ej., puntajes 3–4 en preguntas ligadas a creatividad, lógica, ayuda social, sistemas, organización, etc.).
- No enumeres todas las respuestas; resume tendencias (intereses altos/medios/bajos).
- Relaciona esas tendencias con tareas/ambientes reales de la modalidad elegida.

Perfiles de egresado (elige SOLO la sección que coincida exactamente con la modalidad; si es sub-especialidad, usa la sub-especialidad):

— Académico
• Observación rigurosa, formulación de hipótesis, diseño de experimentos y amor por la verdad y el conocimiento.
• Argumentación ética, pensamiento crítico y creatividad científica en favor de un desarrollo sostenible.

— Agropecuaria (procesamiento de alimentos)
• Alistamiento, limpieza y desinfección; empaque y apoyo a control de procesos en plantas de alimentos y bebidas.
• Perfil operativo/asistencial en panadería, lácteos y fruver; enfoque en calidad y normativas básicas.

— Comercio — Emprendimiento y Fomento Empresarial
• Crear microempresas, apoyar administración de negocios, asesoría de ventas.
• Planear, organizar y comunicar propuestas de valor y acciones comerciales.

— Comercio — Diseño Gráfico
• Apoyo a departamentos de publicidad: diseño de piezas, originales de impresión, criterios de color y tipografía.
• Producción gráfica con claridad y precisión para medios impresos y digitales.

— Comercio — Contabilidad y Finanzas
• Apoyo contable y financiero: registrar, procesar, interpretar y conservar información (manual y sistematizada).
• Roles típicos: auxiliar contable/financiero/facturación/nómina/tesorería.

— Industrial — Mantenimiento de Hardware y Software
• Soporte a infraestructura TI: instalación/configuración, diagnóstico básico, responsabilidad y buenas prácticas.
• Aporte a continuidad operativa en organizaciones públicas/privadas.

— Industrial — Electricidad y Electrónica
• Análisis de circuitos, instalación de redes internas, mantenimiento e instalación eléctrica/electrónica.
• Posibles roles: técnico/auxiliar en mantenimiento, diseño de redes, domicilia, electrodomésticos, seguridad.

— Industrial — Robótica
• Electrónica + programación para automatización; diagnóstico de circuitos; configuración de cómputo; registro técnico.
• Apoyo a digitalización/automatización y programación de operaciones; roles de auxiliar/analista programador.

— Promoción Social — Primera Infancia
• Acompañamiento pedagógico a desarrollo integral en educación inicial/preescolar.
• Base para continuar cadena de formación en atención y cuidado de la primera infancia.

— Promoción Social — Seguridad y Salud en el Trabajo
• Apoyo al SG-SST según normatividad laboral; identificación de riesgos, cultura de autocuidado.
• Roles: auxiliar de prevención, seguridad industrial/laboral, técnico de seguridad.

— Promoción Social — Promoción de la Salud
• Apoyo comunitario para promoción y mantenimiento de la salud; competencias laborales sociales/comunitarias.
• Base para continuar estudios en áreas de la salud y lo social.

Respuestas del test (1=No me interesa, 4=Me gusta):
{respuestas}

Tu tarea:
1) Usa SOLO el perfil que coincida con "{modalidad}" (si trae guion o categoría, p. ej. "Comercio — Contabilidad y Finanzas", usa esa sub-sección).
2) Relaciona tendencias de las respuestas con tareas/entornos de la modalidad (ej.: si hay gusto por creatividad → Diseño Gráfico; si hay gusto por organizar y manejar números → Contabilidad, etc.).
3) Formatea exactamente así (sin emojis en los títulos):

Por qué te lo sugerimos: …
Qué aprenderás: …
Siguientes pasos: …

4) Mantén 90–130 palabras, lenguaje juvenil y concreto.
'''.strip()
    # === FIN DEL BLOQUE EDITADO ===

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
        # Opcional: ajusta a tu gusto
        "temperature": 0.7,
        "max_tokens": 300,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)

        # Logs útiles para depuración
        print("🟡 Groq status:", response.status_code)
        try:
            print("🟡 Groq response body:", response.text[:2000])
        except Exception:
            pass

        if response.status_code == 200:
            payload = response.json()
            return payload["choices"][0]["message"]["content"].strip()

        # Devuelve el mensaje de error de Groq para saber exactamente qué pasó
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
