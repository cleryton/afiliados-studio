# Contrato de interface

Agenda 0.8: calendário separa preparação manual, reserva local de publicação, envio em andamento e agendamento confirmado no YouTube. Data vencida deve aparecer como vencida, sem afirmar que publicou. Quando a rotina redistribui uma reserva, mostrar data anterior e nova data sem anunciar confirmação remota. Manter navegação, tipografia e componentes existentes; ações levam ao roteiro e ao destino apropriado, sem cancelar agendamentos externos localmente. Conferir vazio, planejamento automático, preparação manual, reserva vencida, publicação retida e agendamento confirmado (com dados visuais identificados como simulação), nomes longos e foco em 1440x900 e 390x844.

Continuidade 0.7: o catálogo mostra última tentativa, última atualização aceita e próxima consulta prevista, distinguindo pausa, consulta em andamento e falha com retomada. Falha não aparece como atualização confirmada. O painel não promete publicação nem mostra um prazo quando a consulta está pausada. Conferir leitura e foco do formulário em 1440x900 e 390x844, inclusive mensagem longa e histórico parcial. Dados simulados para esta conferência ficam apenas na memória da página.

Resultados 0.6: origem e data da contagem automática junto das visualizações, campos opcionais como não informados e aviso quando não houver atualização confirmada. Cliques e comissões não informados permanecem desconhecidos. Métricas do tester são identificadas como teste local; nenhuma consulta externa ocorre nesse modo. Validar tabela com dados simulados somente no ambiente tester e estado vazio nos dois viewports.

Operação 0.6: escolha entre texto por trechos e cena completa, deixando explícita a temporização aproximada. Começar mostra fila real com estado e motivo de retenção, sem ETA inventada. Validar escolha persistida, fila vazia, produto pausado, tentativa futura e geração real em 1440x900 e 390x844. Texto variável deve ser observado no MP4 decodificado, preservando roteiro e fonte. Recuperação automática não pode aceitar ou repetir uma tentativa de envio externo. Uma segunda instância no mesmo banco deve ser rejeitada antes de inicializar o banco; normal e tester continuam separados.

Conteúdo 0.5: configuração de roteiro completo ou curto e narração normal ou ágil, com ajuda que distingue estimativa e duração medida. O editor mostra abordagem, extensão e previsão sem prometer alcance. Vídeos usam capítulos visuais, texto legível, foto autorizada opcional e publicidade nos dois formatos. Validar configurações, erro de opção inválida, roteiro anterior sem novos metadados e prévia real em 1440x900 e 390x844. Legendas SRT por trechos usam temporização aproximada, explicitada no painel.

Evolução 0.4: painel editorial com campanhas e fila de revisão. A ação principal da fila é resolver pendências ou aprovar um vídeo pronto; a direção editorial concentra público, estilo, encerramento, pausa e revisão opcional por vídeo. Contadores resumem estados reais, sem nota de qualidade ou ganhos estimados. A prévia acompanha verificações e uma ação de recuperação. A navegação móvel deve permitir rolar horizontalmente os destinos adicionais sem aumentar a largura da página. Confirmar filtro vazio, MP4 antigo sem verificação, erro de validação, aprovação pendente, aprovação concluída e edição que invalida aprovação nos viewports 1440x900 e 390x844. Mudanças locais preservam os limites reais de TikTok e do modo tester.

Superfície: ferramenta local em português para um afiliado cadastrar um produto, revisar um roteiro, gerar MP4 e registrar resultados reais. A primeira tela é **Começar e acompanhar**, com três etapas: autorizar produtos, conectar canal e iniciar. O destino principal é YouTube; a sequência é catálogo autorizado → roteiro → vídeo → envio privado → publicidade confirmada → agendamento → publicação pública confirmada → resultados registrados.

Direção: painel operacional sóbrio, navegação verde escuro, superfícies claras e destaque verde suave. Referência local: o trabalho começa com um link e acompanha estados de produção; por isso, a primeira tela mostra os requisitos reais de ativação e os estados de publicação. O detalhe visual é uma pequena composição de celular sem imagem de produto inventada.

Viewports: 1440x900 e 390x844. A navegação tem rótulos no desktop e ícones com nomes acessíveis no celular. Cartões passam de 3 para 1 coluna e diálogos reorganizam a prévia sobre o formulário. Alvos de ação e foco visível devem funcionar com teclado.

Estados verificáveis:

- Loading: carregamento inicial mantém navegação visível; importação informa leitura em andamento e desabilita o botão.
- Empty: banco inicial vazio oferece cadastro, sem resultados ou vendas fictícios.
- Error: URL inválida e leitura bloqueada mostram texto específico sem apagar dados do formulário.
- Partial: metadados indisponíveis permitem cadastro manual; vídeo sem voz continua disponível com aviso.
- Success: produto salvo aparece no catálogo; MP4 gerado habilita reprodução e download.
- Permission: geração exige revisão dos dados e autorização de materiais; iniciar fica desabilitado sem produtos autorizados e sem canal; autorização Google acontece no navegador e o botão informa publicação pública. TikTok permanece opcional como rascunhos.

Revisar a renderização nos dois tamanhos, formulário, navegação, rolagem horizontal, nomes longos, foco, Escape para fechar o diálogo, mensagens e prévia. Evidências ficam em artifacts/; resultados de teste não entram em data/.

Acompanhamento da operação: verificações locais com estados pronto, pendente, conferir e corrigir. O teste de vídeo deve ter carregamento visível, ser reproduzível no painel e deixar explícito que não publica. Aprendizado de horários distingue resultados não informados de zeros confirmados. Retomar geração deve explicar bloqueios de autorização ou envios externos. Revisar estes estados em desktop e mobile.

Modo tester: faixa permanente em todas as rotas, pasta separada, CTA Criar vídeo de demonstração e manual acessível pelo topo. A demonstração deve identificar o link ilustrativo sem comissão. Google e Buffer não recebem envios; os controles externos avançados ficam desabilitados. Diagnóstico de suporte contém apenas informações técnicas e contagens, sem dados de produtos, contas ou credenciais.
