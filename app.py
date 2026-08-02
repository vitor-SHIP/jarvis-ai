import base64
import os
import sqlite3
from dotenv import load_dotenv
from groq import Groq
import streamlit as st

# Carrega as chaves do arquivo .env
load_dotenv()

# Configuração da página
st.set_page_config(page_title="Jarvis AI", page_icon="🤖", layout="wide")

# Inicializa o cliente do Groq
groq_key = os.environ.get("GROQ_API_KEY")
if not groq_key:
  st.error("Configure sua chave do Groq corretamente no arquivo .env")

client = Groq(api_key=groq_key) if groq_key else None


# --- BANCO DE DADOS LOCAL ---
def init_db():
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


init_db()


def carregar_chats_do_banco():
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
          "SELECT role, content FROM chats WHERE chat_name = ?", (nome,)
      )
      mensagens = []
      for role, content in cursor.fetchall():
        if content.startswith("IMAGE_URL:"):
          img_data = content.replace("IMAGE_URL:", "")
          mensagens.append({
              "role": role,
              "content": [{"type": "image_url", "image_url": {"url": img_data}}],
          })
        else:
          mensagens.append({"role": role, "content": content})
      chats[nome] = mensagens
  conn.close()
  return chats


def salvar_mensagem_banco(chat_name, role, content):
  conn = sqlite3.connect("jarvis_chat.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO chats (chat_name, role, content) VALUES (?, ?, ?)",
      (chat_name, role, content),
  )
  conn.commit()
  conn.close()


def deletar_chat_banco(chat_name):
  conn = sqlite3.connect("jarvis_chat.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM chats WHERE chat_name = ?", (chat_name,))
  conn.commit()
  conn.close()


if "chats" not in st.session_state:
  st.session_state.chats = carregar_chats_do_banco()

if "current_chat" not in st.session_state:
  st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# --- PAINEL LATERAL ESQUERDO ---
with st.sidebar:
  st.markdown("### 🤖 Jarvis AI")

  if st.button("✨ Novo chat", use_container_width=True):
    novo_nome = f"Conversa {len(st.session_state.chats) + 1}"
    st.session_state.chats[novo_nome] = []
    st.session_state.current_chat = novo_nome
    st.rerun()

  st.markdown("<br>", unsafe_allow_html=True)
  st.markdown("**Recentes**")

  for nome_chat in list(st.session_state.chats.keys()):
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
      if st.button(
          nome_chat, key=f"btn_{nome_chat}", use_container_width=True
      ):
        st.session_state.current_chat = nome_chat
        st.rerun()

    with col2:
      if len(st.session_state.chats) > 1:
        if st.button("🗑️", key=f"del_{nome_chat}"):
          deletar_chat_banco(nome_chat)
          del st.session_state.chats[nome_chat]
          st.session_state.current_chat = list(
              st.session_state.chats.keys()
          )[-1]
          st.rerun()

  st.markdown("---")
  st.markdown("### 🖼️ Anexar Imagens")
  uploaded_images = st.file_uploader(
      "Selecione arquivos",
      type=["jpg", "jpeg", "png"],
      accept_multiple_files=True,
      label_visibility="collapsed",
  )

# --- TELA PRINCIPAL ---
mensagens_atuais = st.session_state.chats[st.session_state.current_chat]

if not mensagens_atuais:
  st.markdown(
      "<h2 style='text-align: center; color: #c4c7c5; margin-top: 15vh;'>Olá,"
      " Flávio.</h2>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: #8e918f;'>Como posso ajudar você"
      " hoje?</p>",
      unsafe_allow_html=True,
  )

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

if prompt := st.chat_input("Insira um comando ou faça uma pergunta..."):
  conteudo_mensagem = []
  tem_imagem = False

  if uploaded_images:
    for img in uploaded_images:
      bytes_data = img.getvalue()
      base64_img = base64.b64encode(bytes_data).decode("utf-8")
      img_url = f"data:image/jpeg;base64,{base64_img}"
      conteudo_mensagem.append(
          {"type": "image_url", "image_url": {"url": img_url}}
      )
      salvar_mensagem_banco(
          st.session_state.current_chat, "user", f"IMAGE_URL:{img_url}"
      )
    tem_imagem = True

  if prompt:
    conteudo_mensagem.append({"type": "text", "text": prompt})
    salvar_mensagem_banco(st.session_state.current_chat, "user", prompt)
  elif tem_imagem:
    conteudo_mensagem.append(
        {"type": "text", "text": "Analise esta imagem para mim."}
    )
    salvar_mensagem_banco(
        st.session_state.current_chat,
        "user",
        "Analise esta imagem para mim.",
    )

  mensagens_atuais.append({"role": "user", "content": conteudo_mensagem})

  with st.chat_message("user"):
    for item in conteudo_mensagem:
      if item.get("type") == "text":
        st.markdown(item["text"])
      elif item.get("type") == "image_url":
        st.image(item["image_url"]["url"], width=300)

  chat_atual_nome = st.session_state.current_chat
  if len(mensagens_atuais) == 2 and chat_atual_nome == "Nova Conversa":
    novo_titulo = prompt[:22] + "..." if prompt and len(prompt) > 22 else "Conversa"
    conn = sqlite3.connect("jarvis_chat.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE chats SET chat_name = ? WHERE chat_name = 'Nova Conversa'",
        (novo_titulo,),
    )
    conn.commit()
    conn.close()

    st.session_state.chats[novo_titulo] = st.session_state.chats.pop(
        "Nova Conversa"
    )
    st.session_state.current_chat = novo_titulo
    chat_atual_nome = novo_titulo

  if client:
    with st.chat_message("assistant"):
      with st.spinner("Pensando..."):
        try:
          mensagens_para_enviar = [{
              "role": "system",
              "content": (
                  "Você é o Jarvis, uma inteligência artificial avançada,"
                  " sofisticada e prestativa."
              ),
          }]

          for m in mensagens_atuais:
            role = m["role"]
            content = m["content"]
            if isinstance(content, list):
              texto_combinado = ""
              for item in content:
                if item.get("type") == "text":
                  texto_combinado += item.get("text", "") + " "
                elif item.get("type") == "image_url":
                  texto_combinado += "[Imagem enviada pelo usuário] "
              mensagens_para_enviar.append(
                  {"role": role, "content": texto_combinado.strip()}
              )
            else:
              mensagens_para_enviar.append({"role": role, "content": content})

          chat_completion = client.chat.completions.create(
              messages=mensagens_para_enviar, model="llama-3.3-70b-versatile"
          )
          resposta_final = chat_completion.choices[0].message.content
          st.markdown(resposta_final)

          salvar_mensagem_banco(
              st.session_state.current_chat, "assistant", resposta_final
          )

          mensagens_atuais.append({
              "role": "assistant",
              "content": resposta_final,
          })
          st.rerun()

        except Exception as e:
          st.error(f"Erro ao processar: {e}")
