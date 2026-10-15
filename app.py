import streamlit as st
from google import genai
from google.genai import types

# ============================================================
# 1. CONFIGURACIÓN DE LA APLICACIÓN WEB
# ============================================================

st.set_page_config(
    page_title="NEXA | Sistemas Inteligentes",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 NEXA")
st.caption(
    "UAdeO · Sistemas Inteligentes · "
    "Dra. Aiblis Susej Herrera Palafox"
)

st.markdown(
    "Qué onda, soy **NEXA**. Tu asistente de inteligencia artificial. "
    "Estoy aquí para ayudarte con tus dudas, tareas y problemas de código. "
    "Échale, ¿qué necesitas? 😏"
)

# ============================================================
# 2. CONFIGURACIÓN DE GEMINI
# ============================================================

try:
    API_KEY = st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    API_KEY = ""

if not API_KEY:
    st.error("No encuentro tu clave de Gemini.")
    st.info(
        "Configura GEMINI_API_KEY en el archivo "
        "`.streamlit/secrets.toml` o en los Secrets de Streamlit Cloud."
    )
    st.code(
        'GEMINI_API_KEY = "TU_CLAVE_API"',
        language="toml",
    )
    st.stop()
# ============================================================
# 3. PERSONALIDAD DE NEXA
# ============================================================

CONFIG_INSTRUCCIONES = types.GenerateContentConfig(
    system_instruction="""
    Tu nombre es NEXA.

    Eres una inteligencia artificial creada para la materia
    de Sistemas Inteligentes de la UAdeO.

    PERSONALIDAD:
    - Eres sarcástica, irreverente, bromista y segura de ti misma.
    - Hablas de manera casual, como una persona joven mexicana.
    - Utilizas expresiones mexicanas naturalmente.
    - Puedes usar groserías ocasionales cuando encajen.
    - Te gusta bromear con el usuario y hacer comentarios sarcásticos.
    - Puedes señalar errores con humor, pero nunca humilles al usuario.
    - No eres excesivamente formal ni hablas como un robot.
    - Tienes una actitud segura y un humor ácido.

    FORMA DE RESPONDER:
    - Siempre intenta ser útil, clara y precisa.
    - No inventes información.
    - Si no sabes algo, reconócelo.
    - Explica los temas técnicos paso a paso.
    - Para preguntas sencillas, responde brevemente.
    - Usa Markdown cuando facilite la lectura.
    - Ayuda con programación, tareas, investigación e inteligencia artificial.
    - Explica conceptos como agentes inteligentes y redes neuronales.
    - Si preguntan por fechas o entregas de la materia,
      recomienda revisar las indicaciones de la Dra. Aiblis
      Susej Herrera Palafox.
    - No discrimines ni promuevas violencia.

    REGLA PRINCIPAL:
    Tu personalidad debe hacer la conversación divertida,
    pero nunca debe impedir que ayudes correctamente.

    Si el usuario pregunta quién eres, responde que eres NEXA.
    """,
    temperature=0.9,
    max_output_tokens=1000,
)

# ============================================================
# 4. INICIALIZACIÓN DEL CLIENTE Y LA CONVERSACIÓN
# ============================================================

if (
    "client" not in st.session_state
    or st.session_state.get("current_api_key") != API_KEY
):
    try:
        st.session_state.client = genai.Client(api_key=API_KEY)
        st.session_state.current_api_key = API_KEY

        st.session_state.chat_session = (
            st.session_state.client.chats.create(
                model="gemini-3.8-flash",
                config=CONFIG_INSTRUCCIONES,
            )
        )

    except Exception:
        st.error(
            "No pude conectarme con Gemini. "
            "Revisa tu clave de API y el nombre del modelo."
        )
        st.stop()

# ============================================================
# 5. HISTORIAL DE CONVERSACIÓN
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Qué onda, soy NEXA. 🤖\n\n"
                "¿Qué necesitas? Pásame tu duda y vamos a resolverla. "
                "Prometo no juzgarte demasiado... 😂"
            ),
        }
    ]

# ============================================================
# 6. BARRA LATERAL Y OPCIONES
# ============================================================

with st.sidebar:
    st.header("⚙️ Configuración")

    st.markdown("**Asistente:** NEXA")
    st.markdown("**Modelo:** Gemini 3.8 Flash")
    st.markdown("**Materia:** Sistemas Inteligentes")

    st.divider()

    if st.button(
        "🧹 Limpiar conversación",
        use_container_width=True,
    ):
        try:
            st.session_state.chat_session = (
                st.session_state.client.chats.create(
                    model="gemini-3.8-flash",
                    config=CONFIG_INSTRUCCIONES,
                )
            )

            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Listo, conversación reiniciada. 🧹 "
                        "Borrón y cuenta nueva. ¿Qué sigue?"
                    ),
                }
            ]

            st.rerun()

        except Exception:
            st.error(
                "No pude reiniciar la conversación. "
                "Intenta recargar la página."
            )

    st.divider()

    st.caption(
        "NEXA es un asistente experimental. "
        "Verifica la información importante."
    )

# ============================================================
# 7. MOSTRAR LOS MENSAJES ANTERIORES
# ============================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============================================================
# 8. RECIBIR MENSAJES Y RESPONDER CON GEMINI
# ============================================================

user_input = st.chat_input(
    "Escribe tu pregunta aquí..."
)

if user_input:

    # Mostrar y guardar el mensaje del usuario.
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    # Consultar a Gemini.
    with st.chat_message("assistant"):

        with st.spinner("NEXA está pensando... 🤔"):

            try:
                response = (
                    st.session_state.chat_session.send_message(
                        user_input
                    )
                )

                answer = (
                    response.text
                    or "Esta vez no recibí una respuesta. Inténtalo otra vez."
                )

                st.markdown(answer)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            except Exception as error:
                print(f"Error de Gemini: {error}")

                st.error(
                    "¡Chin! No pude obtener una respuesta de Gemini. "
                    "Revisa tu conexión, tu clave de API y la "
                    "disponibilidad del modelo."
                )
