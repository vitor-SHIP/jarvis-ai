import os
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st

# Carrega chave de ambiente se houver
load_dotenv()
gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

st.set_page_config(page_title="Jarvis Simples", page_icon="🤖", layout="centered")

st.title("🤖 Jarvis - Chat Simples")

if not gemini_key:
    st.error("Chave GEMINI_API_KEY não encontrada nos Segredos do Streamlit ou arquivo .env!")
else:
    genai.configure(api_key=gemini_key)

# Histórico da sessão na memória
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe as mensagens anteriores na tela
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada do usuário
if prompt := st.chat_input("Digite sua mensagem..."):
    # Adiciona a mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gera a resposta do assistente
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                
                if response and response.text:
                    resposta = response.text
                    st.markdown(resposta)
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                else:
                    st.error("A IA não retornou conteúdo.")
            except Exception as e:
                st.error(f"Erro ao conectar com o Gemini: {e}")
