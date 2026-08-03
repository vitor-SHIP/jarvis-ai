import base64
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

# Inicializa o cliente do Groq
if not groq_key:
  st.error("Configure sua chave do Groq nas Secrets do Streamlit ou no arquivo .env")

client = Groq(api_key=groq_key) if groq_key else None

# --- BANCO DE DADOS ---
def init_db():
  try:
      conn = sqlite3.connect("jarvis_chat.db")
      cursor = conn.cursor()
      cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'")
      tabela_existe = cursor.fetchone()
      
      if tabela_existe:
          cursor.execute("PRAGMA table_info(chats)")
          colunas = [col[1] for col in cursor.fetchall()]
          if "content_type" not in colunas:
              cursor.execute("DROP TABLE chats")
              conn.commit()

      cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name TEXT,
                role TEXT,
                content TEXT,
                content_type TEXT DEFAULT 'text'
            )
        """)
      conn.commit()
      conn.close()
  except Exception:
      if os.path.exists("jarvis_chat.db"):
          os.remove("jarvis_chat.db")
      conn = sqlite3.connect("jarvis_chat.db")
      cursor = conn.cursor()
      cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name TEXT,
                role TEXT,
                content TEXT,
                content_type TEXT DEFAULT 'text'
            )
        """)
      conn.commit()
      conn.close()

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
                  "SELECT role, content, content_type FROM chats WHERE chat_name = ? ORDER BY id ASC", (nome,)
              )
              mensagens = []
              for role, content, content_type in cursor.fetchall():
                  if content_type == 'image_base64':
                      mensagens.append({
                          "role": role,
                          "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{content}"}}]
                      })
                  else:
                      mensagens.append({"role": role, "content": content})
              chats[nome] = mensagens
      conn.close()
      return chats
  except Exception:
      return {"Nova Conversa": []}

def salvar_mensagem_banco(chat_name, role, content, content_type='text'):
  try:
      conn = sqlite3.connect("jarvis_chat.db")
      cursor = conn.cursor()
      cursor.execute(
          "INSERT INTO chats (chat_name, role, content, content_type) VALUES (?, ?, ?, ?)",
          (chat_name, role, content, content_type),
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
  st.markdown("### 🖼️ Anexar Imagem")
  uploaded_images = st.file_uploader(
      "Selecione arquivo",
      type=["jpg", "jpeg", "png"],
      accept_multiple_files=True,
      label_visibility="collapsed",
  )

# --- TOPO PERSONALIZADO ---
st.markdown(
    """
    <div style="padding: 15px 20px; background-color: #1e1f20; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333333; display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 24px;">🤖</span>
            <div>
                <h3 style="margin: 0; color: #e3e3e3; font-size: 18px;">Jarvis AI</h3>
                <p style="margin: 0; color: #8e918f; font-size: 12px;">Sistema Operacional Ativo &bull; Llama Vision</p>
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
  st.markdown("<p style='text-align: center; color: #8e918f;'>Como posso ajudar você hoje? Envie um texto ou anexe uma imagem.</p>", unsafe_allow_html=True)

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
          st.markdown(content)

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
              salvar_mensagem_banco(st.session_state.current_chat, "user", base64_img, 'image_base64')
              tem_imagem = True
          except Exception as e:
              st.error(f"Erro ao processar a imagem: {e}")

  if prompt:
      conteudo_mensagem.append({"type": "text", "text": prompt})
      salvar_mensagem_banco(st.session_state.current_chat, "user", prompt, 'text')
  elif tem_imagem:
      texto_padrao = "Analise esta imagem para mim."
      conteudo_mensagem.append({"type": "text", "text": texto_padrao})
      salvar_mensagem_banco(st.session_state.current_chat, "user", texto_padrao, 'text')

  mensagens_atuais.append({"role": "user", "content": conteudo_mensagem})
  st.rerun()

# --- RESPOSTA DA IA COM VISÃO ATUALIZADA ---
if mensagens_atuais and mensagens_atuais[-1]["role"] == "user" and client:
  with st.chat_message("assistant"):
      with st.spinner("Jarvis analisando..."):
          try:
              mensagens_formatadas = [{
                  "role": "system",
                  "content": "Você é o Jarvis, uma inteligência artificial avançada e prestativa com capacidade de visão."
              }]

              for m in mensagens_atuais:
                  mensagens_formatadas.append({"role": m["role"], "content": m["content"]})

              chat_completion = client.chat.completions.create(
                  messages=mensagens_formatadas,
                  model="meta-llama/llama-3.2-90b-vision-instruct" # Modelo atualizado e ativo na Groq
              )

              resposta_final = chat_completion.choices[0].message.content
              st.markdown(resposta_final)

              salvar_mensagem_banco(st.session_state.current_chat, "assistant", resposta_final, 'text')
              mensagens_atuais.append({"role": "assistant", "content": resposta_final})

          except Exception as e:
              st.error(f"Erro na API ao analisar imagem: {e}")
