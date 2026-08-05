import os
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st

# Carrega variáveis de ambiente locais e busca a chave do Gemini
load_dotenv()
gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# Configuração da página do Streamlit
st.set_page_config(page_title="Jarvis - Rastreio & Chat", page_icon="🧭", layout="wide")

if gemini_key:
    genai.configure(api_key=gemini_key)

# --- BANCO DE DADOS ---
def init_db():
    try:
        conn = sqlite3.connect("jarvis_rastreio.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name TEXT,
                role TEXT,
                content TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro no banco: {e}")

init_db()

def carregar_chats():
    try:
        conn = sqlite3.connect("jarvis_rastreio.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT chat_name FROM chats")
        nomes = [row[0] for row in cursor.fetchall()]

        chats = {}
        if not nomes:
            chats["Conversa Principal"] = []
        else:
            for nome in nomes:
                cursor.execute(
                    "SELECT role, content FROM chats WHERE chat_name = ? ORDER BY id ASC", (nome,)
                )
                mensagens = []
                for role, content in cursor.fetchall():
                    mensagens.append({"role": role, "content": content})
                chats[nome] = mensagens
        conn.close()
        return chats
    except Exception:
        return {"Conversa Principal": []}

def salvar_mensagem(chat_name, role, content):
    try:
        conn = sqlite3.connect("jarvis_rastreio.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chats (chat_name, role, content) VALUES (?, ?, ?)",
            (chat_name, role, content),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar: {e}")

def deletar_chat(chat_name):
    try:
        conn = sqlite3.connect("jarvis_rastreio.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chats WHERE chat_name = ?", (chat_name,))
        conn.commit()
        conn.close()
    except Exception:
        pass

if "chats" not in st.session_state:
    st.session_state.chats = carregar_chats()

if "current_chat" not in st.session_state or not st.session_state.chats:
    if not st.session_state.chats:
        st.session_state.chats["Conversa Principal"] = []
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# --- PAINEL LATERAL ---
with st.sidebar:
    st.markdown("### 🧭 Jarvis Rastreio")

    if st.button("✨ Nova Conversa", use_container_width=True):
        novo_id = 1
        while f"Rastreio {novo_id}" in st.session_state.chats:
            novo_id += 1
        novo_nome = f"Rastreio {novo_id}"
        st.session_state.chats[novo_nome] = []
        st.session_state.current_chat = novo_nome
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Histórico**")

    for nome_chat in list(st.session_state.chats.keys()):
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(nome_chat, key=f"btn_{nome_chat}", use_container_width=True):
                st.session_state.current_chat = nome_chat
                st.rerun()

        with col2:
            if len(st.session_state.chats) > 1:
                if st.button("🗑️", key=f"del_{nome_chat}"):
                    deletar_chat(nome_chat)
                    del st.session_state.chats[nome_chat]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[-1]
                    st.rerun()

    st.markdown("---")
    st.markdown("💡 *Modo leve e direto para conversar e rastrear informações.*")

# --- TOPO DA TELA ---
st.markdown(
    """
    <div style="padding: 15px 20px; background-color: #1e1f20; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333333; display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 24px;">🧭</span>
            <div>
                <h3 style="margin: 0; color: #e3e3e3; font-size: 18px;">Jarvis Chat & Rastreio</h3>
                <p style="margin: 0; color: #8e918f; font-size: 12px;">Sistema Operacional Ativo</p>
            </div>
        </div>
        <div style="background-color: #131314; padding: 5px 12px; border-radius: 20px; border: 1px solid #444;">
            <span style="color: #8ab4f8; font-size: 12px; font-weight: bold;">● Online</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- EXIBIÇÃO DO CHAT ---
if st.session_state.current_chat not in st.session_state.chats:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

mensagens_atuais = st.session_state.chats[st.session_state.current_chat]

if not mensagens_atuais:
    st.markdown("<h2 style='text-align: center; color: #c4c7c5; margin-top: 10vh;'>Como posso ajudar a rastrear ou conversar hoje?</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8e918f;'>Digite abaixo o que você quer registrar, buscar ou debater.</p>", unsafe_allow_html=True)

for message in mensagens_atuais:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- ENTRADA DE TEXTO ---
if prompt := st.chat_input("Digite sua mensagem, dúvida ou item para rastrear..."):
    salvar_mensagem(st.session_state.current_chat, "user", prompt)
    mensagens_atuais.append({"role": "user", "content": prompt})
    st.rerun()

# --- RESPOSTA DA IA ---
if mensagens_atuais and mensagens_atuais[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Jarvis processando..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                historico_chat = []
                for m in mensagens_atuais[:-1]:
                    role_map = "user" if m["role"] == "user" else "model"
                    historico_chat.append({"role": role_map, "parts": [m["content"]]})
                
                chat = model.start_chat(history=historico_chat)
                response = chat.send_message(mensagens_atuais[-1]["content"])

                if response and response.text:
                    resposta_final = response.text
                    st.markdown(resposta_final)
                    salvar_mensagem(st.session_state.current_chat, "assistant", resposta_final)
                    mensagens_atuais.append({"role": "assistant", "content": resposta_final})
                    st.rerun()
                else:
                    st.error("A IA não retornou nenhuma resposta.")

            except Exception as e:
                st.error(f"Erro na comunicação com a API: {e}")
