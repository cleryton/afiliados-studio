# Alterações

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
