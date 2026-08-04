import base64
import json
import os
import sqlite3
from io import BytesIO
from dotenv import load_dotenv
from groq import Groq
from PIL import Image
import streamlit as st

# Carrega as chaves
load_dotenv()
groq_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

# Configuração da página
st.set_page_config(page_title="Jarvis AI", page_icon="🤖", layout="wide")

if not groq_key:
    st.error("Configure sua chave do Groq nas Secrets do Streamlit ou no arquivo .env")

client = Groq(api_key=groq_key) if groq_key else None

# --- BANCO DE DADOS ---
def init_db():
    try:
        conn = sqlite3.connect("jarvis_chat.db")
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

def carregar_chats_do_banco():
    try:
        conn = sqlite3.connect("jarvis_chat.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT chat_name FROM chats")
        nomes = [row[0] for row in cursor.fetchall()]

        chats = {}
        if not nomes:
            chats["Nova Conversa"] = []
        else:
            for nome in nomes:
                cursor.execute(
                    "SELECT role, content FROM chats WHERE chat_name = ? ORDER BY id ASC", (nome,)
                )
                mensagens = []
                for role, content in cursor.fetchall():
                    try:
                        content_parsed = json.loads(content)
                    except:
                        content_parsed = content
                    mensagens.append({"role": role, "content": content_parsed})
                chats[nome] = mensagens
        conn.close()
        return chats
    except Exception:
        return {"Nova Conversa": []}

def salvar_mensagem_banco(chat_name, role, content):
    try:
        conn = sqlite3.connect("jarvis_chat.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chats (chat_name, role, content) VALUES (?, ?, ?)",
            (chat_name, role, content),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar: {e}")

def deletar_chat_banco(chat_name):
    try:
        conn = sqlite3.connect("jarvis_chat.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chats WHERE chat_name = ?", (chat_name,))
        conn.commit()
        conn.close()
    except Exception:
        pass

if "chats" not in st.session_state:
    st.session_state.chats = carregar_chats_do_banco()

if "current_chat" not in st.session_state or not st.session_state.chats:
    if not st.session_state.chats:
        st.session_state.chats["Nova Conversa"] = []
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# --- PAINEL LATERAL ---
with st.sidebar:
    st.markdown("### 🤖 Jarvis AI")

    if st.button("✨ Novo chat", use_container_width=True):
        novo_id = 1
        while f"Nova Conversa {novo_id}" in st.session_state.chats:
            novo_id += 1
        novo_nome = f"Nova Conversa {novo_id}"
        st.session_state.chats[novo_nome] = []
        st.session_state.current_chat = novo_nome
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Recentes**")

    for nome_chat in list(st.session_state.chats.keys()):
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(nome_chat, key=f"btn_{nome_chat}", use_container_width=True):
                st.session_state.current_chat = nome_chat
                st.rerun()

        with col2:
            if len(st.session_state.chats) > 1:
                if st.button("🗑️", key=f"del_{nome_chat}"):
                    deletar_chat_banco(nome_chat)
                    del st.session_state.chats[nome_chat]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[-1]
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🖼️ Enviar ou Tirar Foto")
    
    uploaded_images = st.file_uploader(
        "Carregar arquivo",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    camera_image = st.camera_input("Tirar foto")

# --- TOPO PERSONALIZADO ---
st.markdown(
    """
    <div style="padding: 15px 20px; background-color: #1e1f20; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333333; display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 24px;">🤖</span>
            <div>
                <h3 style="margin: 0; color: #e3e3e3; font-size: 18px;">Jarvis AI</h3>
                <p style="margin: 0; color: #8e918f; font-size: 12px;">Sistema Operacional Ativo &bull; Llama 3.3</p>
            </div>
        </div>
        <div style="background-color: #131314; padding: 5px 12px; border-radius: 20px; border: 1px solid #444;">
            <span style="color: #8ab4f8; font-size: 12px; font-weight: bold;">● Online</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- TELA PRINCIPAL ---
if st.session_state.current_chat not in st.session_state.chats:
    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

mensagens_atuais = st.session_state.chats[st.session_state.current_chat]

if not mensagens_atuais:
    st.markdown("<h2 style='text-align: center; color: #c4c7c5; margin-top: 10vh;'>Olá, Flávio.</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8e918f;'>Como posso ajudar você hoje? Envie um texto ou anexe uma foto.</p>", unsafe_allow_html=True)

for message in mensagens_atuais:
    with st.chat_message(message["role"]):
        content = message["content"]
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    st.markdown(item["text"])
                elif item.get("type") == "image_url":
                    st.image(item["image_url"]["url"], width=300)
        else:
            st.markdown(str(content))

if prompt := st.chat_input("Digite uma mensagem ou envie uma imagem..."):
    conteudo_mensagem = []
    tem_imagem = False

    if uploaded_images:
        for img_file in uploaded_images:
            try:
                image = Image.open(img_file)
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.thumbnail((1024, 1024))
                
                buffered = BytesIO()
                image.save(buffered, format="JPEG", quality=85)
                base64_img = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                img_url = f"data:image/jpeg;base64,{base64_img}"
                conteudo_mensagem.append({"type": "image_url", "image_url": {"url": img_url}})
                tem_imagem = True
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")

    if camera_image:
        try:
            image = Image.open(camera_image)
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.thumbnail((1024, 1024))
            
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            base64_img = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            img_url = f"data:image/jpeg;base64,{base64_img}"
            conteudo_mensagem.append({"type": "image_url", "image_url": {"url": img_url}})
            tem_imagem = True
        except Exception as e:
            st.error(f"Erro ao processar foto da câmera: {e}")

    if prompt:
        texto_final = f"[Print do jogo Free Fire anexado]. Pergunta: {prompt}"
        conteudo_mensagem.append({"type": "text", "text": texto_final})
    elif tem_imagem:
        conteudo_mensagem.append({"type": "text", "text": "[Print do jogo Free Fire anexado]. Analise a imagem, diga o que aparece e qual é a cor do cabelo do personagem central."})

    conteudo_json = json.dumps(conteudo_mensagem)
    salvar_mensagem_banco(st.session_state.current_chat, "user", conteudo_json)
    mensagens_atuais.append({"role": "user", "content": conteudo_mensagem})
    st.rerun()

# --- RESPOSTA DA IA ESTÁVEL (Llama 3.3 Versatile) ---
if mensagens_atuais and mensagens_atuais[-1]["role"] == "user" and client:
    with st.chat_message("assistant"):
        with st.spinner("Jarvis analisando..."):
            try:
                mensagens_formatadas = [{
                    "role": "system",
                    "content": "Você é o Jarvis, uma inteligência artificial avançada especialista em jogos, especialmente Free Fire. O usuário envia prints do jogo. Responda diretamente ao usuário descrevendo o cenário, o personagem em destaque, e identifique claramente a cor do cabelo do personagem visível no print."
                }]

                for m in mensagens_atuais:
                    role = m["role"]
                    content_val = m["content"]

                    if isinstance(content_val, list):
                        texto_combinado = " ".join([item.get("text", "") for item in content_val if item.get("type") == "text"])
                        if not texto_combinado.strip():
                            texto_combinado = "O usuário enviou um print do Free Fire."
                        mensagens_formatadas.append({"role": role, "content": texto_combinado})
                    else:
                        mensagens_formatadas.append({"role": role, "content": str(content_val)})

                chat_completion = client.chat.completions.create(
                    messages=mensagens_formatadas,
                    model="llama-3.3-70b-versatile"
                )

                resposta_final = chat_completion.choices[0].message.content
                st.markdown(resposta_final)

                salvar_mensagem_banco(st.session_state.current_chat, "assistant", resposta_final)
                mensagens_atuais.append({"role": "assistant", "content": resposta_final})

            except Exception as e:
                st.error(f"Erro na API: {e}")
