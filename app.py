
import logging
import time

import streamlit as st
from google import genai
from google.genai import types, errors

# ============================================================
# 1. CONFIGURACIÓN DE STREAMLIT
# ============================================================

st.set_page_config(
    page_title="NEXA | Sistemas Inteligentes",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 NEXA")
st.caption("UAdeO · Sistemas Inteligentes · Dra. Aiblis Susej Herrera Palafox")

st.markdown(
    "Qué onda, soy **NEXA**. Tu asistente de inteligencia artificial. "
    "Estoy aquí para ayudarte con tus dudas, tareas y problemas de código. "
    "Échale, ¿qué necesitas? 😏"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexa")


# ============================================================
# 2. CONFIGURACIÓN DE API KEY Y MODELOS
# ============================================================

try:
    API_KEY = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    API_KEY = ""

if not API_KEY:
    st.error("🔑 No encuentro tu clave de Gemini.")
    st.info(
        "Agrega GEMINI_API_KEY a .streamlit/secrets.toml "
        "o a los Secrets de Streamlit Cloud."
    )
    st.code('GEMINI_API_KEY = "TU_CLAVE_API"', language="toml")
    st.stop()


# Puedes sobrescribir los modelos desde secrets.toml.
# El orden indica la prioridad de uso.

DEFAULT_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
]

try:
    configured_models = st.secrets.get("GEMINI_MODELS", "")
except Exception:
    configured_models = ""

if isinstance(configured_models, str) and configured_models.strip():
    MODELS = [
        model.strip()
        for model in configured_models.split(",")
        if model.strip()
    ]
else:
    MODELS = DEFAULT_MODELS

# Elimina duplicados conservando el orden.
MODELS = list(dict.fromkeys(MODELS))


# ============================================================
# 3. PERSONALIDAD DE NEXA
# ============================================================

SYSTEM_INSTRUCTION = """
Tu nombre es NEXA.

Eres una inteligencia artificial creada para la materia
de Sistemas Inteligentes de la UAdeO.

PERSONALIDAD:
- Eres sarcástica, irreverente, bromista y segura de ti misma.
- Hablas casualmente, como una persona joven mexicana.
- Utilizas expresiones mexicanas de manera natural.
- Puedes usar groserías ocasionales cuando encajen.
- Bromeas con el usuario sin humillarlo.
- Tienes humor ácido, pero eres útil y respetuosa.

FORMA DE RESPONDER:
- Sé clara, precisa y útil.
- No inventes información.
- Si no sabes algo, reconócelo.
- Explica los temas técnicos paso a paso.
- Para preguntas sencillas, responde brevemente.
- Usa Markdown cuando ayude a entender.
- Ayuda con programación, tareas e inteligencia artificial.
- Para fechas o entregas de la materia, recomienda revisar
  las indicaciones de la Dra. Aiblis Susej Herrera Palafox.
- No discrimines ni promuevas violencia.

REGLA PRINCIPAL:
Tu personalidad nunca debe impedir que ayudes correctamente.

Si preguntan quién eres, responde que eres NEXA.
"""

CONFIG_INSTRUCCIONES = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    temperature=0.9,
    max_output_tokens=1000,
)


# ============================================================
# 4. INICIALIZAR CLIENTE
# ============================================================

if (
    "client" not in st.session_state
    or st.session_state.get("current_api_key") != API_KEY
):
    try:
        st.session_state.client = genai.Client(api_key=API_KEY)
        st.session_state.current_api_key = API_KEY
        st.session_state.messages = []
        st.session_state.last_model = None

    except Exception:
        logger.exception("No se pudo inicializar el cliente Gemini.")
        st.error("No pude inicializar el cliente de Gemini.")
        st.info(
            "Comprueba tu API key, la conexión a Internet y "
            "que la biblioteca google-genai esté actualizada."
        )
        st.stop()


# ============================================================
# 5. HISTORIAL
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_model" not in st.session_state:
    st.session_state.last_model = None

if "last_error" not in st.session_state:
    st.session_state.last_error = None


def build_contents(messages):
    """
    Reconstruye el historial para enviarlo a cualquier modelo.
    El SDK recibe roles user y model.
    """
    contents = []

    for message in messages:
        role = "user" if message["role"] == "user" else "model"

        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=message["content"])],
            )
        )

    return contents


# ============================================================
# 6. CLASIFICACIÓN DE ERRORES
# ============================================================

def get_error_code(error):
    """Obtiene el código HTTP si el SDK lo proporciona."""
    code = getattr(error, "code", None)

    if code is not None:
        try:
            return int(code)
        except (TypeError, ValueError):
            pass

    return None


def explain_error(error):
    """Convierte los errores técnicos en mensajes comprensibles."""

    code = get_error_code(error)
    message = str(error).lower()

    if code == 400:
        return (
            "⚠️ Gemini rechazó la solicitud. Puede haber un parámetro "
            "incompatible o una configuración no admitida. "
            "Revisa el detalle técnico en los registros."
        )

    if code == 401:
        return (
            "🔑 La autenticación falló. Comprueba que GEMINI_API_KEY "
            "sea correcta y que no haya sido revocada."
        )

    if code == 403:
        return (
            "🔒 Google denegó el acceso. Revisa los permisos, las "
            "restricciones de la clave y la configuración del proyecto."
        )

    if code == 404:
        return (
            "🔎 No se encontró el modelo solicitado. Comprueba su "
            "identificador y que esté disponible para tu proyecto."
        )

    if code == 429:
        return (
            "⏳ Se alcanzó un límite de solicitudes o cuota. "
            "Espera a que se restablezca o revisa los límites de tu proyecto."
        )

    if code in (500, 502, 503, 504):
        return (
            "🚦 Los servidores de Gemini están temporalmente ocupados "
            "o no disponibles. NEXA ya intentó cambiar de modelo. "
            "Inténtalo de nuevo en un momento."
        )

    if code in (408,):
        return (
            "⌛ La solicitud tardó demasiado. Intenta de nuevo "
            "con una pregunta más corta o espera unos segundos."
        )

    if any(term in message for term in (
        "connectionerror",
        "connecterror",
        "network is unreachable",
        "name resolution",
        "temporary failure in name resolution",
    )):
        return (
            "🌐 No pude conectarme con Google. Revisa tu conexión "
            "a Internet, DNS, proxy o firewall."
        )

    if "timeout" in message or "timed out" in message:
        return (
            "⌛ Se agotó el tiempo de espera. Inténtalo de nuevo."
        )

    return (
        "❌ Ocurrió un error inesperado al consultar Gemini. "
        "Revisa los registros para conocer el detalle."
    )


# ============================================================
# 7. CONSULTA CON RESPALDO ENTRE MODELOS
# ============================================================

def ask_gemini(user_prompt):
    """
    Intenta los modelos en orden.
    Devuelve (respuesta, modelo_usado).

    Los errores de autenticación y configuración no se repiten
    en otros modelos porque normalmente afectan a todo el proyecto.
    """

    # Historial previo + nuevo mensaje.
    conversation = list(st.session_state.messages)
    conversation.append({
        "role": "user",
        "content": user_prompt,
    })

    contents = build_contents(conversation)

    last_error = None

    for index, model_name in enumerate(MODELS):
        try:
            response = st.session_state.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=CONFIG_INSTRUCCIONES,
            )

            answer = response.text

            if not answer or not answer.strip():
                raise RuntimeError(
                    f"El modelo {model_name} no devolvió texto."
                )

            # Guardar el modelo que funcionó.
            st.session_state.last_model = model_name

            return answer.strip(), model_name

        except errors.APIError as error:
            last_error = error
            code = get_error_code(error)

            logger.warning(
                "Modelo %s falló con código %s: %s",
                model_name,
                code,
                str(error),
            )

            # No tiene sentido probar los otros modelos si
            # la clave, permisos o solicitud general son incorrectos.
            if code in (400, 401, 403):
                break

            # Para 404, 429, 5xx y otros errores del modelo,
            # continuamos con el siguiente candidato.
            if index < len(MODELS) - 1:
                time.sleep(0.5)

        except Exception as error:
            last_error = error

            logger.exception(
                "Error inesperado con el modelo %s",
                model_name,
            )

            if index < len(MODELS) - 1:
                time.sleep(0.5)

    st.session_state.last_error = last_error
    raise RuntimeError(
        explain_error(last_error)
        if last_error
        else "No hay modelos configurados para consultar."
    )


# ============================================================
# 8. BARRA LATERAL
# ============================================================

with st.sidebar:
    st.header("⚙️ Configuración")
    st.markdown("**Asistente:** NEXA")
    st.markdown("**Materia:** Sistemas Inteligentes")

    st.caption("Modelos configurados:")
    for model in MODELS:
        st.markdown(f"- `{model}`")

    if st.session_state.last_model:
        st.success(
            f"Último modelo utilizado: "
            f"`{st.session_state.last_model}`"
        )

    st.divider()

    if st.button("🧹 Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_error = None
        st.rerun()

    st.divider()

    st.caption(
        "NEXA es un asistente experimental. "
        "Verifica la información importante."
    )


# ============================================================
# 9. MOSTRAR HISTORIAL
# ============================================================

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Qué onda, soy NEXA. 🤖\n\n"
            "¿Qué necesitas? Pásame tu duda y vamos a resolverla. "
            "Prometo no juzgarte demasiado... 😂"
        )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ============================================================
# 10. RECIBIR MENSAJES
# ============================================================

user_input = st.chat_input("Escribe tu pregunta aquí...")

if user_input:
    # Mostrar mensaje del usuario.
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("NEXA está pensando... 🤔"):
            try:
                answer, model_used = ask_gemini(user_input)

                st.markdown(answer)

                # Guardar únicamente cuando se obtiene una respuesta.
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_input,
                })

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                })

                st.session_state.last_error = None

                if model_used != MODELS[0]:
                    st.caption(
                        f"🔄 Respuesta obtenida con el modelo de respaldo "
                        f"`{model_used}`."
                    )

            except RuntimeError as error:
                st.error(str(error))

                # El mensaje no se pierde: se conserva para poder
                # reconstruir el contexto si el usuario reintenta.
                st.session_state.last_error = str(error)

                st.info(
                    "Tu mensaje no se agregó al historial porque "
                    "no se obtuvo respuesta. Puedes enviarlo de nuevo "
                    "cuando el servicio esté disponible."
                )

            except Exception:
                logger.exception("Error no controlado en la aplicación.")
                st.error(
                    "❌ Ocurrió un error inesperado en NEXA. "
                    "Intenta de nuevo y revisa los registros de la aplicación."
                )
