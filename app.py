# --- RESPOSTA DA IA COM VISÃO REAL ---
if mensagens_atuais and mensagens_atuais[-1]["role"] == "user" and client:
    with st.chat_message("assistant"):
        with st.spinner("Jarvis analisando imagem..."):
            try:
                mensagens_formatadas = [{
                    "role": "system",
                    "content": "Você é o Jarvis, uma inteligência artificial avançada especialista em jogos, especialmente Free Fire. Analise a imagem enviada pelo usuário com atenção e diga exatamente o que é, identificando o mapa, personagem, item ou local mostrado."
                }]

                for m in mensagens_atuais:
                    role = m["role"]
                    content_val = m["content"]
                    # Repassa o conteúdo estruturado (texto + imagem em base64) diretamente para o modelo de visão
                    mensagens_formatadas.append({"role": role, "content": content_val})

                chat_completion = client.client.chat.completions.create if hasattr(client, 'client') else client.chat.completions.create
                
                response = client.chat.completions.create(
                    messages=mensagens_formatadas,
                    model="meta-llama/llama-3.2-90b-vision-preview"
                )

                resposta_final = response.choices[0].message.content
                st.markdown(resposta_final)

                salvar_mensagem_banco(st.session_state.current_chat, "assistant", resposta_final)
                mensagens_atuais.append({"role": "assistant", "content": resposta_final})

            except Exception as e:
                st.error(f"Erro na API de Visão: {e}")
