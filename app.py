# --- RESPOSTA DA IA COM O MODELO ATUALIZADO DE VISÃO ---
if mensagens_atuais and mensagens_atuais[-1]["role"] == "user" and client:
  with st.chat_message("assistant"):
      with st.spinner("Jarvis analisando..."):
          try:
              mensagens_formatadas = [{
                  "role": "system",
                  "content": "Você é o Jarvis, uma inteligência artificial avançada e prestativa. Responda de forma direta e concisa."
              }]

              for m in mensagens_atuais:
                  content_val = m["content"]
                  if isinstance(content_val, str):
                      content_val = [{"type": "text", "text": content_val}]
                  
                  mensagens_formatadas.append({
                      "role": m["role"], 
                      "content": content_val
                  })

              chat_completion = client.chat.completions.create(
                  messages=mensagens_formatadas,
                  model="qwen/qwen3.6-27b",
                  reasoning_format="hidden"  # Oculta o pensamento interno do modelo
              )

              resposta_final = chat_completion.choices[0].message.content
              st.markdown(resposta_final)

              salvar_mensagem_banco(st.session_state.current_chat, "assistant", resposta_final, 'text')
              mensagens_atuais.append({"role": "assistant", "content": resposta_final})

          except Exception as e:
              st.error(f"Erro na API ao analisar imagem: {e}")
