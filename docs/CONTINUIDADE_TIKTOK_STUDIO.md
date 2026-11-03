# Continuidade dos envios no TikTok Studio — 0.25

O acesso à pasta de vídeos e o login no TikTok são requisitos separados. O acesso foi conferido no caminho original em um teste local sem transmissão ao TikTok. A integração usa a opção oficial de pasta autorizada. O teste não comprova publicação.

## O que o registro resolve

O estúdio passa a registrar a preparação, o início do upload, a conferência da configuração, a solicitação de agendamento e a confirmação observada. As etapas sobrevivem ao reinício do aplicativo. Repetir uma chamada de preparação retorna a mesma tentativa sem conceder outro upload.

Uma solicitação de agendamento só recebe permissão de execução uma vez. Se a resposta se perder, a rotina precisa conferir a lista do TikTok; não recebe outro disparo automaticamente. Uma tentativa de Studio também impede uma cópia pela integração opcional de API, inclusive se o recibo local ainda não tiver sido gravado.

As duas filas conferem reservas concorrentes dentro da transação de gravação. Se uma rotina ganhar a reserva enquanto a outra valida os arquivos, a segunda é retida antes de receber permissão de envio. Uma atualização atrasada de interrupção também não pode rebaixar uma confirmação já salva.

## Acompanhamento visível no painel

Quando o assistente grava `data/story-week/automation-status.json`, o painel mostra a observação somente para a semana e o perfil atuais. Esse resumo usa códigos fixos, data com fuso e limite de 8 KB. Campos extras, textos de erro e credenciais não são exibidos. Arquivos inválidos geram um aviso de indisponibilidade sem interromper o painel.

Uma observação com mais de 12 horas exige nova conferência e não é apresentada como estado atual do navegador. O aplicativo não conclui que o assistente está ativo pela existência desse arquivo. O acompanhamento depende do Codex em execução, do notebook ligado e da sessão autorizada. Um resumo dizendo que terminou não substitui os recibos dos capítulos.

A próxima ação prioriza a tentativa pendente do capítulo, a pausa e um horário vencido antes de sugerir continuar. Não compensa uma proposta vencida publicando imediatamente.

O primeiro capítulo ainda sem registro da semana tem prioridade. Perfil, pausa, proposta de data, arquivos, link e oferta são conferidos antes de avançar. O operador precisa observar legenda correspondente, visibilidade pública, marcação de IA, publicidade de terceiros quando houver oferta e verificações sem problemas. Uma proposta vencida exige revisão.

## Como funciona a confirmação

Este registro não consulta uma API do TikTok. Ele salva as observações do operador autorizado, que pode ser o assistente usando as ferramentas de navegador. As afirmações de conferência enviadas ao aplicativo precisam corresponder à tela real.

Após um único clique em Agendar, o operador recarrega a lista de conteúdo e confere perfil, link, legenda, data e horário. Só então registra a confirmação. O link deve ser do vídeo no perfil esperado. Uma data passada, uma prévia local ou uma resposta de teste não confirmam publicação.

Se o TikTok já aceitou o pedido e o disco falhar ao salvar o recibo, o resultado confirmado permanece no banco. O cuidado periódico tenta restaurar esse mesmo recibo, sem outro upload. Um recibo existente diferente exige conferência e não é sobrescrito automaticamente. Uma pausa posterior não apaga uma observação real já confirmada.

## Interrupções e verificações

Senha, código e CAPTCHA são concluídos pelo titular. O estúdio pode registrar que é preciso entrar, concluir uma verificação, revisar acesso à pasta ou conferir uma resposta incerta.

Se ainda não houve solicitação de agendamento, a rotina pode retomar uma prévia existente após conferir o mesmo arquivo, o perfil e a ausência de registro na lista recarregada. Essa retomada não concede outro upload. Se já houve solicitação, apenas a conferência do destino pode resolver a tentativa; não há reenvio automático cego.

Na versão 0.26.1, uma falha explícita do seletor antes de aceitar o arquivo tem uma recuperação específica, limitada a uma vez por tentativa. O operador registra o motivo `selector` e confere o seletor vazio, a informação de que o arquivo não foi aceito e a ausência na lista recarregada do perfil. `retry-selection` só libera a seleção do mesmo arquivo, com fontes íntegras e data futura, sem pedido anterior de agendamento. Isso não se aplica a arquivo recusado por permissão, CAPTCHA, resultado perdido ou upload possivelmente aceito.

## Operação pelo assistente

Os caminhos locais de integração são protegidos pelo mesmo token de sessão e pela mesma verificação de origem das outras ações do painel:

- `POST /api/stories/native/begin`: reserva o primeiro capítulo pronto, após observar o perfil correto.
- `POST /api/stories/native/advance`: registra `upload_started` antes do envio e depois `details_checked` e `submission_started`. O resultado `may_dispatch` só é verdadeiro na primeira transição para solicitação. Não clicar em Agendar novamente se esse resultado for falso ou se a resposta se perder.
- `POST /api/stories/native/hold`: registra um motivo fixo para conferência, sem guardar mensagens de login, senhas ou códigos.
- `POST /api/stories/native/resume-preview`: retoma somente uma prévia intacta, observada, sem solicitação anterior de agendamento. Não autoriza outro upload.
- `POST /api/stories/native/retry-selection`: uma recuperação verificada da falha do seletor antes da transferência; não autoriza repetir um agendamento nem contornar permissões.
- `POST /api/stories/native/confirm`: registra a observação do destino recarregado e salva um recibo de agendamento, mantendo publicação efetiva como não confirmada.

Os caminhos acima não executam o navegador. Sem um operador ou uma integração compatível em execução, o aplicativo não publica sozinho. O catálogo de histórias continua finito. O modo tester bloqueia essas tentativas externas; os testes usam arquivos sintéticos e não representam posts reais.

## Coleção mensal 2D

O mesmo registro atende à [reserva mensal de 96 histórias](RESERVA_MENSAL_2D.md). A reserva mantém seus próprios horários e arquivos, sem modificar a semana 3D. O primeiro item mensal ainda sem confirmação tem prioridade; preparar de novo a mesma coleção não concede uploads adicionais.

`POST /api/stories/month/reconcile-owner` existe somente para registrar um agendamento feito pelo titular fora das etapas do assistente, após relato explícito e conferência da lista nativa recarregada. Exige perfil, legenda, visibilidade, URL e data correspondentes, além dos arquivos originais inalterados. Não autoriza outro envio e não se aplica a um pedido já solicitado pelo fluxo normal. A marcação de IA não observada permanece desconhecida e a publicação efetiva permanece não confirmada.
