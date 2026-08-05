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
                    st.error("A IA não retornou nenhuma resposta. Tente enviar novamente.")

            except Exception as e:
                st.error(f"Erro na comunicação com a API: {e}")
