import streamlit as st
import requests
import os
import json

st.set_page_config(page_title="Grok Chat", page_icon="🤖")

def load_dotenv(path='.env'):
    """Very small .env loader: reads KEY=VALUE lines and sets os.environ for missing keys."""
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and not os.getenv(k):
                    os.environ[k] = v
    except Exception:
        pass

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("OPENROUTER_API_KEY is not set. Copy .env.example to .env and set it to your key.")
    st.stop()

URL = "https://openrouter.ai/api/v1/chat/completions"

st.title("Chat with Grok-4-Fast")
st.caption("A minimal Streamlit frontend for OpenRouter (Grok). Your API key stays local in .env.")

# Sidebar controls
st.sidebar.title("Settings")
response_style = st.sidebar.radio("Response style", ["Normal", "Detailed (step-by-step)", "Brief (summary)"], index=0)
max_tokens = st.sidebar.slider("Max tokens", min_value=50, max_value=2000, value=200, step=50)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.5, value=1.0, step=0.1)
show_json = st.sidebar.checkbox("Show full JSON response", value=False)
if st.sidebar.button("Clear chat"):
    st.session_state['messages'] = []

if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Display chat history
for role, content in st.session_state['messages']:
    st.chat_message(role).write(content)

# Input
prompt = st.chat_input("Type your message...")
if prompt:
    # Append and show user message
    st.session_state['messages'].append(("user", prompt))
    st.chat_message("user").write(prompt)

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    # Build messages with an optional system instruction based on response style
    messages = []
    if response_style == "Detailed (step-by-step)":
        messages.append({
            "role": "system",
            "content": "You are an assistant that provides very detailed, step-by-step reasoning and explanations. Do not truncate details; be thorough and explicit in the chain of thought when asked."
        })
    elif response_style == "Brief (summary)":
        messages.append({
            "role": "system",
            "content": "You are an assistant that provides concise summaries. Reply in 1-3 sentences unless asked for more detail."
        })
    # Finally add the user message
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "x-ai/grok-4-fast",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    with st.spinner("Waiting for Grok..."):
        try:
            resp = requests.post(URL, headers=headers, json=payload, timeout=30)
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}")
            st.session_state['messages'].append(("assistant", "(error contacting API)"))
        else:
            # Try parse JSON
            try:
                data = resp.json()
            except ValueError:
                data = None

            if resp.status_code == 200 and data:
                try:
                    reply = data["choices"][0]["message"]["content"]
                except Exception:
                    # Fallback to printing whole JSON
                    reply = json.dumps(data, indent=2)

                # Append assistant message and display depending on style
                st.session_state['messages'].append(("assistant", reply))
                st.chat_message("assistant").write(reply)

                # If user wants the full JSON, show it below
                if show_json:
                    with st.expander("Full JSON response"):
                        st.json(data)
            else:
                body = data if data is not None else resp.text
                st.error(f"Error: {resp.status_code} {body}")
                st.session_state['messages'].append(("assistant", f"(error: {resp.status_code})"))
