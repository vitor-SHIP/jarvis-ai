import base64
import os
import sqlite3
from dotenv import load_dotenv
from groq import Groq
import streamlit as st
import json

# Carrega as chaves (funciona tanto local no .env quanto nas Secrets do Streamlit Cloud)
load_dotenv()
groq_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

# Configuração da página
st.set_page_config(page_title="Jarvis AI", page_icon="🤖", layout="wide")

# Inicializa o cliente do Groq
if not groq_key:
  st.error("Configure sua chave do Groq corretamente nas Secrets do Streamlit ou no arquivo .env")

client = Groq(api_key=groq_key) if groq_key else None

# --- FUNÇÕES DO BANCO DE DADOS (Atualizadas para gerenciar melhor imagens) ---
def init_db():
  conn = sqlite3.connect("jarvis_chat.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_name TEXT,
            role TEXT,
            content TEXT,
            content_type TEXT DEFAULT 'text'  -- 'text' ou 'image_base64'
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
              "SELECT role, content, content_type FROM chats WHERE chat_name = ? ORDER BY id ASC", (nome,)
          )
          mensagens_raw = cursor.fetchall()
          mensagens = []
          for role, content, content_type in mensagens_raw:
              if content_type == 'image_base64':
                  # Reconstrói o formato para o Groq Vision
                  mensagens.append({
                      "role": role,
                      "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{content}"}}]
                  })
              else:
                  # Mensagem de texto padrão
                  mensagens.append({"role": role, "content": content})
          chats[nome] = mensagens
  conn.close()
  return chats

def salvar_mensagem_banco(chat_name, role, content, content_type='text'):
  conn = sqlite3.connect("jarvis_chat.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO chats (chat_name, role, content, content_type) VALUES (?, ?, ?, ?)",
      (chat_name, role, content, content_type),
  )
  conn.commit()
  conn.close()

def deletar_chat_banco(chat_name):
  conn = sqlite3.connect("jarvis_chat.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM chats WHERE chat_name = ?", (chat_name,))
  conn.commit()
  conn.close()

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "chats" not in st.session_state:
  st.session_state.chats = carregar_chats_do_banco()

if "current_chat" not in st.session_state:
  # Garante que exista pelo menos um chat
  if not st.session_state.chats:
      st.session_state.chats["Nova Conversa"] = []
  st.session_state.current_chat = list(st.session_state.chats.keys())[0]

# --- PAINEL LATERAL ESQUERDO ---
with st.sidebar:
  st.markdown("### 🤖 Jarvis AI")

  if st.button("✨ Novo chat", use_container_width=True):
      novo_id = 1
      # Cria um nome único para a nova conversa
      while f"Nova Conversa {novo_id}" in st.session_state.chats:
          novo_id += 1
      novo_nome = f"Nova Conversa {novo_id}"
      st.session_state.chats[novo_nome] = []
      st.session_state.current_chat = novo_nome
      st.rerun()

  st.markdown("<br>", unsafe_allow_html=True)
  st.markdown("**Recentes**")

  # Exibe os chats salvos
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
                  # Seleciona o chat anterior se existir
                  st.session_state.current_chat = list(st.session_state.chats.keys())[-1]
                  st.rerun()

  st.markdown("---")
  st.markdown("### 🖼️ Anexar Imagens (Para Visão)")
  uploaded_images = st.file_uploader(
      "Selecione arquivos",
      type=["jpg", "jpeg", "png"],
      accept_multiple_files=True,
      label_visibility="collapsed",
  )

# --- TOPO PERSONALIZADO (CABEÇALHO) ---
st.markdown(
    """
    <div style="padding: 15px 20px; background-color: #1e1f20; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333333; display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 24px;">🤖</span>
            <div>
                <h3 style="margin: 0; color: #e3e3e3; font-size: 18px;">Jarvis AI</h3>
                <p style="margin: 0; color: #8e918f; font-size: 12px;">Sistema Operacional Ativo &bull; Llama 3.3 Vision</p>
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
mensagens_atuais = st.session_state.chats[st.session_state.current_chat]

if not mensagens_atuais:
  st.markdown("<h2 style='text-align: center; color: #c4c7c5; margin-top: 10vh;'>Olá,"
              f" {os.environ.get('USER_NICKNAME', 'Flávio')}.</h2>", unsafe_allow_html=True)
  st.markdown("<p style='text-align: center; color: #8e918f;'>Como posso ajudar você"
              " hoje? Envie um texto ou anexe uma imagem para análise.</p>", unsafe_allow_html=True)

# Exibe as mensagens atuais do chat
for message in mensagens_atuais:
  with st.chat_message(message["role"]):
      content = message["content"]
      if isinstance(content, list):
          # Processa lista de conteúdo (pode ter imagem)
          for item in content:
              if item.get("type") == "text":
                  st.markdown(item["text"])
              elif item.get("type") == "image_url":
                  # O Streamlit aceita a URL de dados base64 diretamente
                  st.image(item["image_url"]["url"], width=300)
      else:
          # Mensagem de texto padrão
          st.markdown(content)

# Captura nova entrada do usuário
if prompt := st.chat_input("Insira um comando, faça uma pergunta ou anexe uma imagem..."):
  conteudo_mensagem = []
  tem_imagem = False
  base64_images_for_db = []

  # Processa as imagens enviadas
  if uploaded_images:
      for img in uploaded_images:
          bytes_data = img.getvalue()
          base64_img = base64.b64encode(bytes_data).decode("utf-8")
          base64_images_for_db.append(base64_img)

          # Estrutura para o Groq Vision
          img_url = f"data:image/jpeg;base64,{base64_img}"
          conteudo_mensagem.append({"type": "image_url", "image_url": {"url": img_url}})

          # Salva no banco (conteúdo é a string base64, tipo 'image_base64')
          salvar_mensagem_banco(st.session_state.current_chat, "user", base64_img, 'image_base64')
      tem_imagem = True

  # Adiciona o texto e salva no banco
  if prompt:
      conteudo_mensagem.append({"type": "text", "text": prompt})
      salvar_mensagem_banco(st.session_state.current_chat, "user", prompt, 'text')
  elif tem_imagem:
      # Se não tiver prompt de texto, mas tiver imagem, adiciona um texto padrão
      texto_padrao = "Analise esta(s) imagem(ns) para mim."
      conteudo_mensagem.append({"type": "text", "text": texto_padrao})
      salvar_mensagem_banco(st.session_state.current_chat, "user", texto_padrao, 'text')

  # Adiciona ao estado da sessão e exibe na interface do usuário
  mensagens_atuais.append({"role": "user", "content": conteudo_mensagem})

  # Re-renderiza a interface para mostrar a mensagem do usuário instantaneamente
  st.rerun()

# --- GERAÇÃO DA RESPOSTA PELO GROQ ---
# Verificamos se a última mensagem é do usuário para disparar a resposta da IA
if mensagens_atuais and mensagens_atuais[-1]["role"] == "user" and client:
  with st.chat_message("assistant"):
      with st.spinner("Jarvis está processando..."):
          try:
              # Cria uma cópia das mensagens formatadas para enviar à API (com as imagens codificadas)
              mensagens_formatadas_para_groq = [{
                  "role": "system",
                  "content": "Você é o Jarvis, uma inteligência artificial avançada, sofisticada e prestativa. Você agora possui capacidades de visão."
              }]

              # Adiciona o histórico
              for m in mensagens_atuais:
                  mensagens_formatadas_para_groq.append({
                      "role": m["role"],
                      "content": m["content"] # O formato é compatível com a API de visão
                  })

              # Chama a API com o modelo Vision
              chat_completion = client.chat.completions.create(
                  messages=mensagens_formatadas_para_groq,
                  model="llama-3.2-11b-vision-preview" # Usando o modelo específico para visão
              )

              resposta_final = chat_completion.choices[0].message.content
              st.markdown(resposta_final)

              # Salva a resposta da IA no banco de dados
              salvar_mensagem_banco(st.session_state.current_chat, "assistant", resposta_final, 'text')

              # Adiciona a resposta da IA ao estado da sessão e re-renderiza
              mensagens_atuais.append({"role": "assistant", "content": resposta_final})

          except Exception as e:
              st.error(f"Erro ao processar (verifique se a imagem é muito grande ou o formato não é suportado): {e}")
