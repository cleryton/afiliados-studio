# Postagem de histórias no TikTok

## Estado real e custo

A versão 0.17 inclui uma integração opcional com a API do Upload-Post. Na conta gratuita conferida em 25/10/2026, o próprio painel informou que conectar TikTok exige plano pago. A página pública anuncia dez uploads gratuitos e perfis TikTok, mas isso não confirmou liberação do TikTok nesta conta. O estúdio não contrata, atualiza planos ou cadastra cartões. A integração fica pausada até existir acesso confirmado ao perfil de destino.

Como alternativa sem mensalidade de integração, o TikTok Studio pode oferecer agendamento no próprio envio. O arquivo e as marcações precisam ser enviados e o agendamento confirmado na plataforma; ter o MP4 pronto no estúdio local não significa ter uma postagem agendada. Essa alternativa não envia automaticamente novos arquivos do notebook.

Fontes: [documentação de envio e restrição do plano Free](https://docs.upload-post.com/api/upload-video/), [perfis e identificação de conta](https://docs.upload-post.com/api/user-profiles), [consulta de status](https://docs.upload-post.com/api/upload-status).

## Configurar a integração opcional

Em **Histórias no TikTok → Postagem automática no TikTok**, use apenas o perfil exclusivo do projeto. Ele deve estar conectado no provedor com autorização do titular. No Upload-Post, **API Keys → Create Key** cria uma chave. Cole-a somente no campo protegido do estúdio local e clique em **Conectar postagem**. Não envie a chave no chat nem em relatórios de suporte.

O Windows protege a chave com DPAPI, vinculada ao usuário do computador. A chave não aparece no estado do aplicativo, no banco de configurações, em mensagens ou no GitHub. Conectar verifica o @ e guarda também a identificação estável da conta fornecida pelo provedor. Uma troca de conta exige nova conferência, mesmo se o nome do perfil for parecido.

Depois de conectar, escolha o horário em São Paulo, ative os envios públicos e confirme o perfil e as marcações. É possível agendar o piloto 3D pronto ou colocar prévias 3D completas automaticamente na agenda. Atualizar o mesmo capítulo não cria uma nova postagem: o identificador do conteúdo e o hash do vídeo evitam repetição. O piloto atual é finito; a rotina não inventa novas temporadas.

## Envio e limites

O notebook precisa estar ligado, com internet e com o estúdio em execução. A agenda é local. Limites conservadores: um pedido de envio por dia e dez por mês, além das regras e da cota do próprio provedor. Uma reserva vencida pode ser enviada quando o programa voltar, respeitando esses limites. Não há promessa de melhores horários sem dados reais de audiência.

Antes de transmitir, o sistema confere novamente a conta, o MP4, a legenda, o link e a autorização do produto. Envia o arquivo local, sem tornar o painel público, com marcação de parceria de terceiros quando existe oferta e indicação de IA. Não adiciona músicas, direitos de anúncios, comentários ou destinatários extras.

O pedido recebe uma identificação persistente, usada como chave de idempotência e consulta de status. Erro de rede, encerramento durante envio ou resposta desconhecida não repetem o upload. O sistema consulta o mesmo pedido; pode exigir conferência no provedor. Não há botão de reenvio cego. Pausar impede novos envios e permite continuar conferindo pedidos já transmitidos.

## Ler os estados

- **Na agenda local**: reservado no notebook; não foi confirmado no TikTok.
- **Enviando / Aguardando confirmação**: o pedido está em execução; ainda não há confirmação pública.
- **Conferindo pedido sem reenviar**: resposta incerta; o upload não será repetido.
- **Publicado e confirmado**: resposta de sucesso do TikTok pelo provedor com link do perfil esperado.
- **Entregue como rascunho**: não foi publicado automaticamente; não é tratado como sucesso público.
- **Envio retido / Conferir identificação**: conta, material, cota, plano ou marcações precisam de atenção. Não contratar planos nem repetir manualmente sem conferir o pedido anterior.

O modo tester bloqueia conexão, ativação e envio externos. Os testes usam respostas simuladas e arquivos identificados como fixtures; isso não comprova uma publicação real.
