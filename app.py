# Converte o histórico garantindo texto para as mensagens anteriores e formato correto para a última
              mensagens_formatadas = [{
                  "role": "system",
                  "content": "Você é o Jarvis, uma inteligência artificial avançada com capacidade de visão. Responda de forma direta e concisa."
              }]

              for i, m in enumerate(mensagens_atuais):
                  role = m["role"]
                  content_val = m["content"]
                  is_last_message = (i == len(mensagens_atuais) - 1)

                  if isinstance(content_val, list):
                      if is_last_message:
                          # Envia a imagem real para o modelo vision na última mensagem
                          mensagens_formatadas.append({"role": role, "content": content_val})
                      else:
                          # Histórico antigo vira texto para não estourar o limite da API
                          texto_limpo = " ".join([item.get("text", "") for item in content_val if item.get("type") == "text"])
                          mensagens_formatadas.append({"role": role, "content": texto_limpo if texto_limpo else "[Imagem enviada]"})
                  else:
                      mensagens_formatadas.append({"role": role, "content": str(content_val)})

              # USANDO O MODELO COM SUPORTE A VISÃO DA GROQ
              chat_completion = client.chat.completions.create(
                  messages=mensagens_formatadas,
                  model="llama-3.2-11b-vision-preview"
              )
