import base64
import json
import os
import sqlite3
from io import BytesIO
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
import streamlit as st

# Carrega as chaves
load_dotenv()
gemini_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# Configuração da página
st.set_page_config(page_title="Jarvis AI", page_icon="🤖", layout="wide")

if not gemini_key:
    st.error("Configure sua chave do Google Gemini (GEMINI_API_KEY) nas Secrets do Streamlit ou no arquivo .env")

# Inicializa o cliente do Gemini
client = genai.Client(api_key=gemini_key) if gemini_key else None

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
                <p style="margin: 0; color: #8e918f; font-size: 12px;">Sistema Operacional Ativo &bull; Google Gemini Vision</p>
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
    st.markdown("<p style='text-align: center; color: #8e918f;'>Como posso ajudar você hoje? Envie um texto ou anexe uma foto do Free Fire.</p>", unsafe_allow_html=True)

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
    imagem_pil = None

    if uploaded_images:
        for img_file in uploaded_images:
            try:
                image = Image.open(img_file)
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.thumbnail((1024, 1024))
                imagem_pil = image # Guarda para o Gemini
                
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
            imagem_pil = image
            
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=85)
            base64_img = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            img_url = f"data:image/jpeg;base64,{base64_img}"
            conteudo_mensagem.append({"type": "image_url", "image_url": {"url": img_url}})
            tem_imagem = True
        except Exception as e:
            st.error(f"Erro ao processar foto da câmera: {e}")

    if prompt:
        conteudo_mensagem.append({"type": "text", "text": prompt})
    elif tem_imagem:
        conteudo_mensagem.append({"type": "text", "text": "O que tem nesta imagem do Free Fire?"})

    conteudo_json = json.dumps(conteudo_mensagem)
    salvar_mensagem_banco(st.session_state.current_chat, "user", conteudo_json)
    mensagens_atuais.append({"role": "user", "content": conteudo_mensagem})
    st.rerun()

# --- RESPOSTA DA IA COM O GOOGLE GEMINI (VISÃO REAL) ---
if mensagens_atuais and mensagens_atuais[-1]["role"] == "user" and client:
    with st.chat_message("assistant"):
        with st.spinner("Jarvis analisando a imagem visualmente..."):
            try:
                # Prepara o histórico para o formato do Gemini
                contents_historico = []
                
                for m in mensagens_atuais:
                    role = m["role"]
                    content_val = m["content"]
                    
                    # Converte o papel para o padrão aceito pelo SDK do Gemini (user / model)
                    gemini_role = "user" if role == "user" else "model"
                    
                    partes_conteudo = []
                    if isinstance(content_val, list):
                        for item in content_val:
                            if item.get("type") == "text":
                                partes_conteudo.append(item["text"])
                            elif item.get("type") == "image_url":
                                # Converte a URL base64 de volta para objeto PIL Image para o Gemini analisar perfeitamente
                                header, encoded = item["image_url"]["url"].split(",", 1)
                                img_bytes = base64.b64decode(encoded)
                                img_obj = Image.open(BytesIO(img_bytes))
                                partes_conteudo.append(img_obj)
                    else:
                        partes_conteudo.append(str(content_val))
                        
                    contents_historico.append(types.Content(
                        role=gemini_role,
                        parts=[types.Part.from_bytes(data=p.tobytes(), mime_type="image/jpeg") if isinstance(p, Image.Image) else types.Part.from_text(text=str(p)) for p in partes_conteudo]
                    ))

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents_historico,
                    config=types.GenerateContentConfig(
                        system_instruction="Você é o Jarvis, uma inteligência artificial especialista em jogos, especialmente Free Fire. Você consegue ver perfeitamente as imagens enviadas pelo usuário, identificando skins, cores de cabelo, personagens, armas e elementos visuais com total precisão."
                    )
                )

                resposta_final = response.text
                st.markdown(resposta_final)

                salvar_mensagem_banco(st.session_state.current_chat, "assistant", resposta_final)
                mensagens_atuais.append({"role": "assistant", "content": resposta_final})

            except Exception as e:
                st.error(f"Erro ao processar com o Gemini: {e}")
