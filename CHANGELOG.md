# Alterações

## 0.28.1-beta — 02/11/2026

- O encerramento normal aguarda até 15 segundos pela leitura do painel ampliado, preservando a conferência de instalação, o token da sessão e a consulta rápida de disponibilidade. Evita interrupção prematura quando a biblioteca semanal cresce.

## 0.28.0-beta — 02/11/2026

- Ampliação de 21 para 28 histórias: sete mistérios originais às 15h, preservando os arquivos, horários, legendas e recibos anteriores.
- Novos episódios podem usar os clipes locais de caminhada, entrega da chave e revelação do desenho, com conferência do vídeo, projeto e medidas do movimento. Narração e montagem são produzidas para cada roteiro.
- Preparação idempotente, com retenção de horários vencidos, colisões, alterações de oferta e pedidos existentes. Contagens de arquivos e registros do TikTok continuam separadas.

## 0.27.0-beta — 01/11/2026

- Três ações originais em 3D: caminhada até a porta, entrega de uma chave e revelação de um desenho. Articulações dos braços e pernas preservam as proporções dos modelos, com verificações de alcance e apoio dos pés a cada quadro.
- Comando explícito de produção local e galeria para assistir e baixar os clipes sem áudio. Os projetos editáveis e as medições permanecem no notebook.
- Demonstrações separadas dos capítulos e das filas de postagem. O catálogo só muda depois que os três MP4s são exportados e decodificados com sucesso.

## 0.26.1-beta — 01/11/2026

- Uma única recuperação de falha explícita do seletor anterior à transferência, após conferir seletor vazio, arquivo não aceito e ausência no destino recarregado.
- A recuperação preserva a mesma tentativa e nunca libera outra solicitação de agendamento. Respostas incertas, alterações de fonte, horários vencidos e tentativas já solicitadas permanecem retidas.

## 0.26.0-beta — 01/11/2026

- Ampliação idempotente da semana para três histórias por dia: 14 roteiros inéditos às 12h e 21h, preservando os sete horários e recibos anteriores.
- Catálogo adicional com conflitos e desfechos próprios; narração e montagem novas usando o banco de animação 3D original. Oferta comercial permanece separada da ficção.
- Calendário e contagens passam a refletir 21 horários. Datas vencidas, colisões, pausas e alterações de oferta ou perfil bloqueiam a ampliação, sem publicar imediatamente nem refazer os vídeos anteriores.

## 0.25.0-beta — 01/11/2026

- Painel mostra a última observação do acompanhamento, o impedimento registrado e a necessidade de nova conferência após 12 horas. O registro não é apresentado como conexão ao vivo.
- Próxima ação considera tentativas nativas pendentes e horários vencidos antes de sugerir outro envio. Contagens continuam vindo dos recibos reais.
- Reservas simultâneas pelo Studio e pela API são conferidas na mesma transação de gravação. Uma atualização atrasada de falha não pode apagar um resultado já confirmado.
- Leitura limitada do resumo local, sem expor campos arbitrários ou credenciais. Arquivos inválidos não derrubam o painel.

## 0.24.0-beta — 01/11/2026

- Registro persistente das etapas de envio no TikTok Studio, com uma única permissão de solicitação, ordem dos capítulos e proteção contra duplicação por outra integração.
- Retomada de uma prévia observada sem conceder outro upload. Solicitações incertas exigem conferência do destino.
- Confirmação baseada na observação do operador após recarregar a lista do TikTok; recibos ausentes podem ser recuperados do resultado já registrado sem retransmitir.
- Painel de continuidade e documentação dos limites: login e verificações pertencem ao titular; o registro de etapas não executa o navegador sozinho.

## Após 0.23 — 31/10/2026

- Reparador da autorização de arquivos do navegador: usa a opção oficial `--workspace` com somente `data/stories`, versão fixa, cópia de recuperação, conferência prévia e aplicação idempotente.
- Orientações para recarregar a integração e validar o upload no caminho original. Nenhum túnel, cópia alternativa, alteração do verificador ou publicação automática é feito pelo reparador.

## 0.23.0-beta — 31/10/2026

- Quadro da operação semanal com contagens distintas de arquivos, agendamentos registrados, publicações confirmadas e pendências, acompanhado de um guia de uso nas férias.
- Fila opcional de postagem usa os capítulos fixados no calendário em ordem, mantém propostas futuras e espera por capítulos incompletos ou pedidos que precisam de revisão.
- Nova conferência de perfil, conexão, pausa e registros nativos imediatamente antes de transmitir. Validações sem transmissão não consomem a cota local diária. Hash do MP4 é calculado por leitura em fluxo.
- Integração externa continua opcional e desativada na operação gratuita. Nenhum envio novo é declarado sem confirmação real.

## 0.22.0-beta — 29/10/2026

- Espera automática por espaço e retomada de falhas temporárias com estado persistente, ordem preservada e limite de três tentativas reais. Pausa manual não é desfeita pela rotina.
- Recuperação de vídeo já concluído, inclusive após falha ao empacotar, sem outra renderização do mesmo item.
- Cuidado periódico verifica os arquivos e repara apenas pacotes a partir de fontes íntegras. Alterações essenciais exigem revisão. Reparos de pacote têm limite próprio.
- Limpeza apenas de cópias temporárias idênticas com arquivo principal preservado. Não remove projetos, publicações ou pastas inteiras.
- Painel mostra o próximo item sem registro, prévia, cópia da legenda, pacote, esperas e controles de pausa/conferência. Não envia mídia ao TikTok.

## 0.21.0-beta — 28/10/2026

- Sete histórias originais completas para a próxima coleção, com roteiro e decisão de montagem fixados por posição do calendário. Protege os agendamentos anteriores.
- Cortes entre enquadramentos da animação em movimento, mantendo a linha de tempo; legendas guiadas por eventos de palavras da voz local, com estimativa identificada se faltarem eventos válidos.
- Revisão automática de voz, abertura, duração e leitura; o pacote exige revisão correspondente ao roteiro. Não atribui nota de viralização.
- Experimento limitado de ritmo somente com observações suficientes, maduras e recentes de vídeos diferentes. Métricas continuam sendo registradas pelo titular, sem sincronização automática.
- Conferência de espaço livre, descarte de cópias temporárias verificadas e retomada manual de preparação interrompida, sem refazer capítulos prontos ou enviar mídia.

## 0.20.0-beta — 25/10/2026

- Plano local de sete dias, com duas continuações prontas e cinco capítulos originais do arco O último desenho. Datas propostas não são marcações do TikTok.
- Produção serial em processo separado, trava entre processos, reaproveitamento de arquivos prontos, recuperação de montagens concluídas e parada em caso de erro ou alteração do destino/produto. Não envia mídia.
- Banco de movimento 3D original com um desenho geométrico novo; roteiros e narrações novos sobre gestos e câmeras já produzidos. Exportação registra o reaproveitamento e a ausência de sincronização labial com o novo áudio.
- Pacotes com MP4, capa original, legenda, SRT e manifesto de destino/marcações. Conferência de hashes, autorização da oferta e registro de postagem antes de preparar/baixar; recibos e fila evitam novo envio do mesmo capítulo.

## 0.19.0-beta — 25/10/2026

- Biblioteca de capítulos 3D, com registros nativos de programação separados de publicação confirmada. Registros de agendamento também bloqueiam uma tentativa duplicada pela integração opcional.
- Limpeza local de versões substituídas: conserva os capítulos atuais, qualquer recibo de postagem, itens da fila e projetos nativos. Confere hashes e caminhos antes de excluir; versões retiradas deixam de aparecer como downloads prontos e não voltam a ser geradas ao mudar a oferta.
- Validador mantém falha para testes incompletos, com limite de doze minutos após um timeout observado no Windows com Python 3.11.

## 0.18.0-beta — 25/10/2026

- Continuação 3D original nos capítulos 2 e 3, com conflito na abertura, legenda própria, pergunta sobre a história e bloco comercial final mais breve. Mantém link, publicidade e identificação de IA.
- Painel de métricas informado pelo titular: observações por vídeo, campos desconhecidos distintos de zero, taxas somente com denominadores disponíveis e sem somar contagens acumuladas. Links restritos ao perfil indicado e datas futuras recusadas.
- Roteiros apresentados como hipóteses, sem horário vencedor ou crescimento presumido. Formulário preserva preenchimento durante atualização de andamento. Manual do tester e testes de validação, retenção, continuidade e chaves de capítulo.

## 0.17.0-beta — 25/10/2026

- Cena da revelação em 3D com abertura da boca e expressão acompanhando a intensidade da voz; continua sem alinhamento por fonema. Reaproveitamento de cinco clipes locais verificados, preservando projetos e a prévia anterior até concluir.
- Integração opcional com Upload-Post, chave protegida pelo Windows, perfil confirmado por identificador estável, agenda local e marcações de publicidade/IA. O plano gratuito observado bloqueou a conexão TikTok; nenhum plano pago é contratado pelo aplicativo.
- Fila persistente com idempotência, limites de um pedido diário e dez mensais, verificação de materiais e conta, retenção de alterações e consulta de pedidos incertos sem repetir upload. Rascunho não é publicação confirmada.
- Painel distingue conexão, ativação, reserva local e confirmação pública. Acesso direto à configuração pelo link `?setup=publishing#stories`, com foco no campo protegido. Modo tester bloqueia operações externas.

## 0.16.0-beta — 25/10/2026

- Piloto original em animação 3D local com Blender: atores modelados, braços articulados, cabeça, olhos, objetos, câmera e porta em movimento. Projetos nativos com animações gravadas e fotografia incorporada.
- Geração opcional de seis trechos, narração e legendas, com publicidade autorizada separada da ficção. Prévia completa exibida no painel, preservando episódios existentes e publicações externas.
- Exportação registra resolução e taxa originais, gestos procedurais e boca sem alinhamento por fonema. Geração interrompida não substitui a prévia pronta anterior.
- Testes de disponibilização da prévia, arquivos incompletos, caminhos inválidos e retirada da autorização comercial. Sem serviços pagos ou instalação automática do Blender pelo aplicativo.

## 0.15.0-beta — 25/10/2026

- Montagem local com tomadas de até quatro segundos, planos de reação e detalhes; objetos fotográficos com transparência animados separadamente do fundo, sem reiniciar a câmera nas trocas de legenda.
- Ambiente e efeitos originais de metal, papel e porta, com voz normalizada e limitação de volume. Sem músicas baixadas ou serviços pagos.
- Clipes próprios por cena, com autorização explícita, origem e hash; enquadramento vertical, repetição de clipes curtos e registro no roteiro. Vídeo inválido preserva o MP4 anterior.
- Botão para remontar um episódio pronto, sem duplicar a temporada ou alterar publicações externas. Personagens ainda sem atuação corporal ou sincronização labial.
- Testes de continuidade dos planos, movimento independente dos objetos, áudio, autorização de clipes, renderização real e proteção da remontagem local.

## 0.14.0-beta — 24/10/2026

- Oferta opcional de afiliado vinculada a produto ativo e autorizado, com publicidade separada da ficção, link preservado e verificação de mudanças nos dados. Perfil de destino indicado sem fingir autenticação ou publicação automática.

- Área Histórias no TikTok com minissérie original de três episódios e desfecho, separada dos produtos e envios de afiliados.
- Imagens realistas de personagens fictícios preparadas com IA; montagem local vertical com movimento de câmera, narração pt-BR, identificação de ficção/IA e legendas por trechos.
- Fila local sem duplicação do piloto, retomada após reinício, prévias e downloads MP4/SRT/legenda. Não conecta nem publica no TikTok; geração contínua de imagens e novas temporadas permanece indisponível.
- Testes de fila, separação de produtos, proteção de arquivos, falha e decodificação real do MP4. Manual descreve criação de perfil exclusivo e os limites da integração TikTok.

## 0.6.0-beta — 22/10/2026

- Texto por trechos dentro do próprio MP4, com cartões equilibrados para evitar uma última palavra isolada; alternativa de cena completa mantida.
- Aberturas mais compactas, com nome do produto e público contextualizados sem acrescentar benefícios não cadastrados.
- Fila com conferência de autorização, pausa, disponibilidade da fonte e tentativas externas antes de iniciar a renderização.
- Atualizações do produto ou campanha refazem roteiros automáticos antes de renderizar; edições manuais desatualizadas são preservadas e exigem recriação explícita.
- Retomada automática de gerações locais interrompidas, com espera de 2 e 10 minutos e parada após três falhas. Envios externos não são repetidos.
- Bloqueio por pasta de dados impede duas instâncias de usarem o mesmo banco; buffers temporários de renderização são limpos mesmo após falhas.
- Fila visível em Começar e acompanhar, com motivo de retenção e tentativa programada. Rascunhos do Buffer também respeitam pausas antes do compartilhamento.
- Renovação da sessão local após reinício só repete uma solicitação explicitamente recusada antes da execução; falhas de rede e envios incertos não são repetidos.
- Catálogos que renumeram um item com o mesmo link não deixam o produto bloqueado por um registro antigo.
- Consulta automática de visualizações, curtidas e comentários públicos do YouTube, em lotes limitados e a cada seis horas por vídeo. Falhas têm espera, snapshots expiram e resultados de afiliado não são inferidos nem alterados.

## 0.5.0-beta — 22/10/2026

- Aberturas por produto, estilo e público, com alternativas para reduzir repetição no histórico.
- Roteiro completo ou curto; o modo curto alterna até duas características verificadas por variação.
- Narração natural ou ágil e previsão de duração, atualizada após editar o roteiro.
- Composição de vídeo com capítulos visuais, foto em painel de contraste e publicidade nos dois formatos.
- Legendas SRT em trechos de até duas linhas, com tempos aproximados distribuídos pelo texto.
- Hashtags derivadas do tipo e da categoria do produto; características e link de afiliado preservados.
- Leitura de um produto identificado em JSON-LD, com características explícitas e alternativa por metadados HTML; listas ambíguas não misturam produtos.
- Catálogo autorizado atualiza os dados também ao reutilizar um produto cadastrado manualmente com o mesmo link.
- Atualizações do catálogo preservam pausa, autorização e limite de variações definidos pelo usuário; disponibilidade da fonte continua bloqueando itens removidos, inativos ou desatualizados.
- Pillow atualizado para 13.0.0 após a auditoria identificar vulnerabilidades na versão anterior.
- Python mínimo passa a 3.11, conforme o requisito do Pillow corrigido; instalador orienta a recriação de ambientes antigos, e CI verifica Python 3.11, 3.12 e 3.13.

## Repositório e validadores — 19/10/2026

- Repositório público após varredura do histórico e dos pacotes publicados.
- Verificações automáticas em pushes e pull requests, com testes Windows em Python 3.10, 3.11 e 3.12.
- Validação local de fontes, recursos do painel, histórico de caminhos privados e integridade do pacote.
- Ruff, Gitleaks e pip-audit em etapas próprias; atualizações de dependências propostas pelo Dependabot.
- Guia dos validadores e comando validar.bat para clones Git.

## 0.4.0-beta — 18/10/2026

- Campanhas com público, estilo, encerramento, pausa e revisão automática ou manual por vídeo.
- Fila de revisão com prévia, filtros, pendências verificáveis e recriação de roteiro com a campanha atual.
- Decodificação real do MP4, conferência de dimensões/duração e vínculo ao roteiro renderizado.
- Aprovação vinculada ao conteúdo, produto, campanha e arquivo; mudanças invalidam a revisão anterior.
- Bloqueios editoriais antes do envio ao YouTube ou de rascunhos ao Buffer; pausa e retenção local não substituem a gestão de agendamentos já enviados no destino.
- Interface adaptada ao celular e manual ampliado. Envio real em canal autorizado continua pendente de validação.

## 0.3.0-tester — 18/10/2026

- Modo tester em banco separado, com bloqueio de contas e publicações externas.
- Demonstração local do cadastro até o MP4, com reutilização do trabalho existente.
- Instalação das dependências em ambiente Python do próprio projeto.
- Manual do usuário tester, ajuda no painel e diagnóstico de suporte sem credenciais.
- Testes de proteção do modo tester e de privacidade do diagnóstico.

## Recursos anteriores

Geração local de vídeo, narração Windows, SRT, rotina de produção, catálogo JSON autorizado, aprendizado de horários com resultados registrados e integração YouTube com upload retomável. As integrações de publicação foram verificadas com respostas simuladas; nenhum envio real é declarado como validado nesta versão.
