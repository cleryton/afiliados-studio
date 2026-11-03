# Reserva mensal de animações 2D

A reserva contém 96 histórias completas em quatro mundos: gato, robô padeiro, guarda-chuva e farol. São quatro propostas por dia, às 12h, 15h, 18h e 21h de São Paulo, durante 24 dias. Os quatro pilotos concluídos são reaproveitados; os outros 92 roteiros têm produção própria. Os agendamentos anteriores permanecem separados.

## Acompanhar no painel

Abra **Histórias no TikTok → Reserva do mês**. O painel separa roteiros e horários, vídeos concluídos e agendamentos observados no TikTok. A lista completa mostra a situação de cada horário. Os primeiros vídeos prontos sem recibo aparecem para assistir ou baixar.

**Pausar produção e próximos envios** impede novas montagens e reservas de envio. Uma montagem em andamento pode terminar. A pausa não remove nem altera o que o TikTok já aceitou. **Retomar** habilita o cuidado local novamente; uma falha de produção continua exigindo revisão de sua causa.

O notebook precisa ficar ligado com o aplicativo em execução para produzir. O acompanhamento pelo navegador depende também do Codex em execução, da integração disponível e da sessão autorizada. Depois de aceito pelo TikTok, o agendamento fica sob responsabilidade da plataforma. Passar do horário não confirma publicação pública no painel.

## Produção e retomada

A produção é serial e não usa serviços pagos. Cada roteiro é fixado com uma soma de verificação antes da geração. O projeto original, a legenda e os arquivos concluídos ficam no notebook. O produtor confere imagem, movimento e áudio antes de liberar cada MP4. Uma falha de voz não libera um vídeo silencioso.

O aplicativo pode retomar a fila após reiniciar. Antes de montar novamente um item interrompido, confere se o arquivo exato já foi concluído. Há limite de duas tentativas por item; erros suspendem novos trabalhos para revisão. Falta de espaço aguarda pelo menos 350 MB livres, com nova conferência pelo serviço local. Intermediários novos de voz e trilha podem ser removidos somente depois da validação do filme; os vídeos anteriores e os projetos são preservados.

O catálogo é finito. A produção não inventa novos produtos, afiliações, resultados de vendas ou novas temporadas. Esta coleção é ficção sem oferta comercial e mantém indicação de IA e narração sintética. A boca usa expressões, sem sincronização por fonemas.

## Agendar sem duplicação

O calendário local é uma proposta. Um operador autorizado, inclusive o assistente com a integração disponível, precisa observar o perfil correto e recarregar a lista nativa antes de enviar. A janela de datas deve ser conferida no calendário do TikTok; a disponibilidade pode variar por conta.

O fluxo mensal usa os mesmos registros de continuidade descritos em [Continuidade no TikTok Studio](CONTINUIDADE_TIKTOK_STUDIO.md): reserva, início de um único upload, conferência das configurações, solicitação única e confirmação após recarregar o destino. Use a legenda do próprio arquivo e confira a marcação nativa de IA, visibilidade, horário e verificações da plataforma. Não interprete demora no envio como permissão para retransmitir.

Se o titular clicar em **Agendar** fora do fluxo do painel, não clique de novo. A reconciliação só registra esse pedido após relato explícito do titular e conferência de perfil, legenda, link, visibilidade e horário na lista recarregada. Ela conserva como desconhecidas as configurações não observadas, inclusive a marcação nativa de IA; não fabrica uma etapa de envio do assistente.

Login, CAPTCHA, códigos, conta diferente, acesso recusado ao arquivo e respostas incertas interrompem a ação correspondente. O titular resolve autenticação e verificações no próprio site. Uma proposta vencida ou indisponível exige revisão, sem publicação imediata para compensar. Não usar cópias em outra pasta, túneis ou outro provedor para contornar um pedido incerto.

## Consulta local e arquivos

- `cartoon_month.py state`: resumo compacto, sem alterar a coleção.
- `cartoon_month.py calendar`: atualiza o calendário local a partir dos registros.
- `data/cartoon-month/CALENDARIO.md`: propostas e estados; não é recibo do TikTok.
- `data/cartoon-month/worker/worker.log`: produção em segundo plano.
- `data/cartoon-month/projects/<id>/`: projeto e roteiro fixado de cada novo filme.
- `data/stories/<id>/`: MP4, capa, legenda, SRT, metadados e eventual recibo nativo.

Não execute `core.init()` como auxiliar no banco em uso. Não execute novamente a produção dos quatro pilotos para preencher a reserva: os quatro arquivos existentes já estão vinculados. Os diretórios de dados permanecem privados e fora do Git.

O acompanhamento recorrente pode continuar os próximos horários quando houver sessão disponível. Ele deve conservar o primeiro pedido ainda sem confirmação, evitar notificações repetidas para um mesmo bloqueio e encerrar ao concluir os 96 registros observados. O resumo em `data/cartoon-month/automation-status.json` é apenas a última observação do acompanhamento, sem credenciais; não substitui os recibos.
