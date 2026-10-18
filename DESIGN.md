# Contrato de interface

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
