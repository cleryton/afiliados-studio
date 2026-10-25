# Afiliados Studio

[![Validadores](https://github.com/cleryton/afiliados-studio/actions/workflows/validate.yml/badge.svg)](https://github.com/cleryton/afiliados-studio/actions/workflows/validate.yml)

Aplicativo local para Windows. Cria roteiros, vídeos com narração e legendas, e integra o envio e agendamento ao YouTube pela API oficial. Sem assinatura de IA ou hospedagem. Energia e internet continuam sendo custos da operação.

Para o TikTok, consulte [conta e limites atuais da publicação](docs/TIKTOK.md). Ter uma conta é necessário para usar o canal, mas a integração atual continua em exportação manual ou rascunhos opcionais; criar a conta não libera postagem pública automática.

Requer Python 3.11 ou superior (recomendado 3.12). Ao atualizar de uma versão anterior à 0.5, execute **instalar.bat** novamente para instalar as dependências corrigidas. Se houver um ambiente `.venv` com Python antigo, o instalador explica como recriá-lo sem apagar `data` e `data-tester`.

**Situação atual:** fontes na versão 0.18.0-beta. Geração local de histórias e agendamento nativo de uma versão 3D no TikTok Studio foram conferidos em conta do projeto. Isso não comprova alcance, vendas ou comissões. O YouTube pessoal e a rotina antiga de afiliados permanecem desativados nesta operação. A postagem automática por integração TikTok continua pendente de acesso compatível. Ofertas comerciais exigem afiliação aprovada e link próprio; lucro não é garantido. O sistema não cria contas, não aceita contratos em seu nome nem inventa links que pagam comissão.

## Conteúdo e resultados do TikTok

A versão 0.18 acrescenta roteiros curtos dos capítulos 2 e 3 em 3D, com conflito na abertura, continuidade e publicidade final mais breve. O painel permite registrar visualizações, interações e retenção reais, preservando dados indisponíveis e comparando a última observação de cada vídeo. A coleta ainda é manual, sem melhor horário ou crescimento presumidos. Veja [Conteúdo e resultados](docs/ENGAJAMENTO_TIKTOK.md).

## Postagem das histórias

A versão 0.17 acrescenta uma integração opcional com Upload-Post, fila persistente, marcações de publicidade/IA, proteção contra duplicação e confirmação por link do destino. Na conta gratuita conferida, o provedor bloqueou TikTok até contratar plano pago; por isso a conexão permanece pendente. O aplicativo não contrata planos. Agendar no próprio TikTok Studio é uma alternativa com envio do arquivo pela plataforma, separada da agenda local. Veja [Postagem TikTok](docs/POSTAGEM_TIKTOK.md).

## Animação 3D local

A versão 0.16 acrescenta um piloto curto com personagens e cenário modelados em 3D, gestos articulados, expressões e porta em movimento, produzido localmente com Blender. Quando concluído, ele aparece em **Histórias no TikTok → Novo · Animação 3D**. O movimento da boca é aproximado; não há alinhamento por fonema, caminhada ou criação contínua de temporadas. A geração usa um comando próprio, separado da fila comum. Veja [Animação 3D](docs/ANIMACAO_3D.md).

## Histórias no TikTok

A versão 0.14 acrescenta **Histórias no TikTok** ao painel: prepare o piloto original **A chave do 12**, com três episódios, personagens realistas gerados por IA, narração local e legendas. Os arquivos são verticais, 720 × 1280. As imagens do piloto já acompanham as fontes; não há serviço automático de geração de novas imagens ou novas temporadas. A versão 0.15 acrescenta cortes em tomadas de até quatro segundos, planos de reação, objetos animados em camadas e efeitos sonoros locais. Os personagens continuam sem atuação corporal ou sincronização labial. Clipes próprios autorizados podem substituir as cenas. Veja [Cenas em movimento](docs/CENAS_EM_MOVIMENTO.md).

Essa fila somente cria arquivos locais e não envia ao YouTube, ao Buffer ou às suas contas pessoais. Crie um perfil exclusivo para o projeto e conclua a publicação no TikTok enquanto não houver integração compatível. A criação da conta depende dos dados, termos e verificações concluídos pelo titular. Consulte [o guia do TikTok](docs/TIKTOK.md) e [o manual do tester](docs/MANUAL_TESTER.md).

## Entrega para testers

Comece por [docs/MANUAL_TESTER.md](docs/MANUAL_TESTER.md). Execute **instalar.bat** uma vez e depois **iniciar_tester.bat**. Esse modo usa um banco separado em data-tester e bloqueia contas e envios externos. Uma demonstração completa pode ser criada pelo painel, sem afiliado ou Google. O manual também está no link Manual no topo da aplicação.

Para relatar falhas, use **Manual → Baixar diagnóstico sem credenciais** e o formulário de Issues do repositório. As verificações rodam automaticamente no GitHub a cada push e pull request: testes Windows, sintaxe, privacidade, pacote, Ruff, Gitleaks e auditoria de dependências. Consulte [docs/VALIDACAO.md](docs/VALIDACAO.md). Em um clone Git, **validar.bat** executa as verificações locais e os testes sem abrir o aplicativo.

## Abrir

Dê dois cliques em `iniciar.bat` ou execute:

```powershell
python -m pip install -r requirements.txt
python background.py start --open
```

Abra http://127.0.0.1:8765/#start. O início normal funciona em segundo plano: mantenha o notebook ligado e com internet. Fechar a página do painel não encerra o programa; use parar.bat para encerrar. A rotina impede suspensão automática enquanto está ativa, sem modificar permanentemente o plano de energia. Fechar a tampa pode suspender o notebook conforme a configuração do Windows.

## Continuidade sem acompanhamento (0.10)

Na versão 0.12, **iniciar.bat** executa em segundo plano, sem depender de uma janela de terminal aberta. **iniciar_console.bat** e **iniciar_tester.bat** mantêm a execução visível para diagnóstico e testes. As três opções usam um supervisor. Se o processo do aplicativo cair inesperadamente, ele tenta reabrir até cinco vezes, após 5, 15, 30, 60 e 120 segundos. Depois de uma hora contínua, uma nova queda começa outra sequência. O navegador abre somente na primeira execução. Encerrar normalmente, usar Ctrl+C, já existir outra instância ou faltar configuração de instalação/porta não provoca reinícios. No modo console ou tester, mantenha a janela aberta. Iniciar diretamente com `python app.py` não usa esse supervisor. A retomada respeita pausas e autorizações salvas e não cria novo upload para um envio incerto.

Planejamento, produção, entrega, catálogo, fotos e cópias do banco têm ciclos independentes. Um erro inesperado em uma rotina aguarda 5, 15, 60 e até 300 segundos antes de tentar o próximo ciclo; operações de catálogo, imagens e renderização mantêm também suas próprias esperas e limites. O checklist mostra falhas, início e ciclos demorados. Um ciclo demorado pede conferência; o programa não dispara outro ciclo concorrente para tentar substituí-lo.

O banco recebe uma cópia local verificada ao abrir e a cada 24 horas de operação, em **data/backups** (ou **data-tester/backups**). Conservamos até sete cópias com nomes gerados pelo programa. A cópia usa a API de backup do SQLite, confere integridade e referências, registra SHA-256 local e preserva a última cópia válida se a próxima falhar. Falhas aguardam 30 minutos. A operação requer 512 MB livres mais margem para o banco, limitado a 256 MB; ela não preenche o disco com tentativas ilimitadas. Fragmentos de cópias interrompidas são descartados antes da próxima tentativa.

Essas cópias contêm cadastros, links pessoais, roteiros, configurações e registros de envio: mantenha-as privadas. Não incluem os arquivos separados de credenciais, fotos ou vídeos. Não são enviadas ao GitHub ou a um serviço externo e não substituem uma cópia em outro disco. Restaurar requer análise dos envios existentes no destino; não há restauração automática que possa reapresentar uma publicação antiga. **Não substitua o banco enquanto o programa estiver aberto.**

Para iniciar automaticamente ao entrar na sua conta do Windows, execute **ativar_inicio_windows.bat**. Para retirar esse início automático, execute **desativar_inicio_windows.bat**; o programa atual continua aberto até executar **parar.bat**. A opção usa somente a entrada de inicialização do usuário atual, sem serviço do Windows ou privilégios de administrador. Outra instalação com a mesma entrada é preservada. O caminho da pasta e o ambiente Python precisam continuar disponíveis. Após atualizar arquivos Python, encerre e abra novamente para carregar a versão nova. Computador desligado, tampa que suspende o notebook, falta de rede, autorização vencida e configuração inicial pendente continuam limitando a operação. O teste privado em conta real foi confirmado; a publicação pública comercial permanece pendente de validação.

## Configuração inicial

### Validar a operação antes da afiliação (0.11)

Em **Começar → Teste completo antes da afiliação**, clique **Criar vídeo de teste**. O programa cria e verifica um clipe próprio identificado como teste privado, sem oferta nem link comercial. Não exige produto cadastrado ou conta de afiliado. Ao terminar, assista à prévia. A geração não envia nada ao YouTube.

Com o clipe pronto e a credencial salva, **Conectar e testar em privado** abre o navegador padrão do Windows. Ao concluir pessoalmente o consentimento Google, o teste inicia sozinho. O botão da etapa 02 permite conectar somente o canal, sem iniciar envio. Se já estiver conectado, use **Autorizar envio privado e iniciar**. O teste usa a API oficial e sempre pede visibilidade **privada**, sem agenda ou notificação aos inscritos. Só aparece como confirmado depois de consultar o vídeo processado, privado e pertencente ao canal autorizado. Não ativa a rotina pública, não cria produto, não registra venda e não altera cliques ou comissões. O modo tester permite a preparação local e bloqueia o envio.

Uma autorização Google pendente passa a ser protegida pelo Windows e persistida por até dez minutos, com uso único: reiniciar o programa durante esse intervalo permite continuar o mesmo retorno; uma nova tentativa invalida a anterior. Senha e consentimento continuam no Google. Erro ou expiração exige abrir uma nova autorização.

Os registros privados do processo ficam em **data/background.log**, com rotação de até dois arquivos de 2 MB. Não compartilhe esses arquivos sem revisar: eles podem conter caminhos e detalhes de operação. O relatório de suporte continua sem credenciais. **iniciar.bat** reaproveita uma instância saudável; **parar.bat** pede encerramento local autenticado, sem procurar ou matar outros processos Python. Agendamentos já confirmados no destino precisam continuar sendo gerenciados lá.

Existe um único teste persistido por instalação: novos cliques não geram outro vídeo nem abrem outro upload. A sessão existente pode continuar após reiniciar. Uma interrupção ou resposta incerta durante a abertura do envio exige conferir o YouTube Studio; o programa não abre outro upload para substituir uma tentativa sem confirmação. Falhas de consulta usam esperas de 1, 2, 5, 15 e 30 minutos; após seis falhas, o teste pausa e oferece retomada. Pausar o teste é independente de pausar a rotina. Uma requisição já iniciada pode terminar no destino como privada.

Para esse teste, a única conta necessária é a sua conta Google com canal YouTube, API habilitada e credencial OAuth de aplicativo para computador. O login, a confirmação de identidade e o consentimento do titular precisam ser concluídos pelo próprio usuário no Google; não envie senha ou código ao suporte. Afiliar produtos vem depois de confirmar o fluxo técnico. O envio em uma conta real só está validado quando houver o resultado confirmado no seu painel.

### Ativar ofertas comerciais

Para o primeiro envio comercial no mesmo dia, conclua as etapas abaixo e aguarde o vídeo automático ficar pronto. Na **Fila de revisão**, assista e clique **Publicar agora no YouTube**. O pedido vale para aquele roteiro e canal; mantém as demais reservas. O programa verifica o MP4, fonte, autorização e identificação comercial antes de pedir visibilidade pública. Só registra publicação depois de uma leitura da API confirmá-la. O botão não transforma o teste privado em oferta comercial e não funciona no modo tester.

O pedido imediato é persistido por até 30 minutos. Se houver resposta incerta ao mudar a visibilidade, o sistema consulta o mesmo vídeo, sem abrir outro upload. Se o YouTube continuar informando privado, a publicação não é considerada concluída. Confira o Studio e eventuais restrições do projeto. Para um vídeo já enviado com falha, vincule o vídeo privado existente antes de fazer um novo pedido. Um pedido expirado sem qualquer sessão externa pode ser renovado pelo botão, após nova conferência das verificações.

1. Crie sua conta num programa de afiliados, obtenha aprovação e gere ao menos um link de afiliado seu. O painel oferece acesso à Kiwify: busque o produto em Marketplace e, depois da aprovação, pegue o link em Produtos → Minhas afiliações → Ver links. Links físicos e digitais de outras plataformas também podem ser cadastrados. O sistema identifica os domínios kiwify.com e kiwify.com.br; isso identifica a plataforma, sem comprovar afiliação ou comissão.
2. Em **Começar e acompanhar**, adicione o produto, as características verificadas e uma foto autorizada opcional. Clique **Autorizar** para permitir o uso desses dados nas variações automáticas.
3. No [Google Cloud](https://console.cloud.google.com/apis/library/youtube.googleapis.com), crie um projeto e habilite **YouTube Data API v3**. Configure o consentimento OAuth e o público externo com seu e-mail como usuário de teste. Crie uma credencial OAuth do tipo **Aplicativo para computador** e baixe o JSON. Não é uma chave de API comum nem credencial de aplicativo Web.
4. Selecione o JSON no campo local do painel e clique **Salvar configuração Google**. Depois clique **Autorizar meu canal no Google** e conclua o consentimento na conta que possui seu canal. O programa usa retorno HTTP apenas no endereço de loopback local e PKCE; não pede senha Google.
5. Ative os [recursos avançados do canal](https://support.google.com/youtube/answer/13748639?hl=pt-BR) para disponibilizar links externos clicáveis nas descrições. O formato padrão é horizontal, 1280 × 720, para publicar como vídeo comum; links nas descrições de Shorts não são clicáveis.
6. Clique **Iniciar criação e publicação automática**. A publicação será pública no canal conectado. No primeiro início, a rotina começa em até um minuto: prepara um vídeo por dia às 18h de Brasília, com antecedência de até três vídeos. Ao retomar, mantém seus ajustes de ritmo e geração. O horário é um ponto inicial de teste, sem evidência de que seja o melhor para seu público. Ajustes ficam em **Modo automático**.

Projetos OAuth externos com status **Testing** recebem refresh tokens que expiram em 7 dias para este escopo. Reconecte quando solicitado. Para operação contínua, configure o status do aplicativo no Google conforme as exigências aplicáveis; sair do modo de teste e verificações são gerenciados no Google Cloud. Documentação: [expiração de tokens](https://developers.google.com/identity/protocols/oauth2#expiration), [autorização para aplicativos desktop](https://developers.google.com/identity/protocols/oauth2/native-app), [envio de vídeos](https://developers.google.com/youtube/v3/docs/videos/insert).

## Criação de conteúdo

Na versão 0.9, o catálogo aceita o campo opcional **`image_url`** com o endereço público de uma foto do produto. Para baixar e usar a foto, marque a autorização específica no formulário do catálogo remoto ou na importação do arquivo JSON. A opção começa desmarcada. Sem ela, nenhum download de foto é iniciado. Use somente fotos que você tenha autorização para divulgar; o sistema verifica o arquivo, não a licença nem a correspondência visual com o produto.

São aceitas fotos estáticas JPG, PNG e WebP de até 5 MB, com pelo menos 64 pixels por lado e até 16 megapixels. O importador limita leituras e prazos, rejeita endereços privados e usa as mesmas proteções de conexão do catálogo. A imagem é decodificada, orientada conforme EXIF, reduzida para até 1600 × 1600 e convertida em um novo JPEG local sem os metadados originais; transparência fica sobre fundo branco. Não executa conteúdo da fonte nem baixa fotos sugeridas automaticamente ao ler uma página de loja.

A rotina de fotos tenta até duas fotos por ciclo de um minuto, em fila própria. Falhas aguardam 5, 15, 60 e depois até 240 minutos, com prazos persistidos. Fotos prontas podem ser conferidas novamente a cada 24 horas. Uma falha conserva a última foto válida quando ainda autorizada e permite continuar com texto. Não aguarda a foto para selecionar ou gerar um vídeo. Fotos manuais são preservadas. Produtos ou campanhas pausados não iniciam novos downloads; a pausa da produção não desliga a consulta independente do catálogo.

Retirar a autorização de fotos remotas, mudar o endereço do catálogo remoto, remover o produto ou retirar/trocar `image_url` desassocia a foto gerenciada anterior. Uma resposta de download antiga não substitui a escolha atual. Pausar somente a consulta remota mantém a foto já autorizada, mas suspende novos downloads. Uma importação de arquivo tem sua própria autorização de fotos e substitui a lista ativa, como antes. Arquivos antigos não são apagados automaticamente, inclusive para preservar gerações em andamento; mantenha espaço para as mídias locais.

Uma foto nova altera os dados visuais do produto: trabalhos automáticos locais sem edição e sem tentativa externa podem ser refeitos pelas regras de continuidade. Edições manuais continuam exigindo revisão. Vídeos já encaminhados a um destino não são substituídos. Em **Começar → Fotos do catálogo**, acompanhe pendências e falhas. O modo tester bloqueia downloads externos de fotos; use imagens próprias no cadastro ou testes controlados de desenvolvimento.

Na versão 0.6, **Texto na tela → Trechos curtos** passa a mostrar partes do roteiro durante a cena, dentro do próprio MP4. Não depende de ativar legendas no destino. Os trechos são equilibrados e preservam as palavras do roteiro; sua temporização é aproximada, distribuída pelo texto e pela duração da cena. **Cena completa** mantém a apresentação anterior. As opções valem para novos roteiros ou após recriar um roteiro local. Arquivos anteriores não são alterados automaticamente.

Em **Modo automático → Criação de conteúdo**, escolha roteiro **Completo** (até quatro características) ou **Curto** (até duas por vídeo), formato e ritmo da voz. O modo curto alterna os detalhes entre variações. As aberturas consideram nome do produto, estilo e público da campanha; a criação procura uma alternativa quando a abertura já aparece no histórico daquele produto.

Os dados continuam vindo do cadastro: informe características específicas e confirmadas, como material, medidas, compatibilidade ou conteúdo incluído. O gerador não acrescenta experiência de uso, resultados, descontos ou benefícios que não tenham sido informados. A leitura do link depende do que a página pública oferece; revise os dados sugeridos.

Na leitura do link, o sistema tenta identificar um único [produto em JSON-LD](https://schema.org/Product) e aproveitar descrição, material, cor, tamanho, modelo e características adicionais explícitas. Sem esse formato, usa título e descrição HTML. Listas ambíguas não combinam características de produtos diferentes. Não executa scripts da loja, não baixa fotos nessa leitura e não infere comissão ou aprovação da afiliação. O link original é mantido.

Cada vídeo tem capítulos visuais, identificação de publicidade e encerramento. Uma foto autorizada aparece em um painel com contraste; sem foto, usa tipografia e numeração de cenas. Hashtags seguem o tipo e a categoria cadastrados. A estimativa de tempo no editor é uma previsão de leitura, não um limite garantido; a duração real é medida na verificação do MP4.

A narração usa a voz pt-BR instalada no Windows, em ritmo natural ou ágil. O SRT divide o texto em trechos de até duas linhas, com temporização aproximada calculada a partir do texto e da duração das cenas; não é alinhamento exato palavra por palavra. A legenda do post mantém o link e a identificação de publicidade.

As configurações valem para novos roteiros. Para aplicá-las a um vídeo local existente, use **Recriar roteiro com a campanha atual**, revise e gere o MP4 novamente. Isso substitui a edição local anterior e invalida a aprovação. Vídeos com tentativa de envio externo permanecem protegidos contra substituição local.

## Campanhas e revisão editorial

Em **Campanhas**, defina o público ou contexto, o estilo da abertura e o encerramento. Vincule produtos e escolha se o sistema pode continuar após as verificações ou se exige aprovação de cada vídeo. Um produto pertence a uma campanha por vez. Produtos sem campanha continuam com a configuração padrão. A campanha não aprova sua afiliação nem substitui a autorização dos materiais.

A **Fila de revisão** reúne prévia, estado real e verificações: roteiro, link preservado, publicidade, autorização, dados atuais, campanha ativa e MP4. Cada nova renderização decodifica o arquivo e confere dimensões e duração. Arquivos de versões anteriores podem ser conferidos em **Verificar arquivo**. Isso confere a consistência técnica e os dados cadastrados; não avalia a veracidade de todas as alegações nem prevê vendas.

Na revisão manual, clique **Aprovar vídeo** depois de assistir. **Solicitar ajustes** bloqueia a continuidade. Mudar roteiro, produto, campanha ou arquivo invalida a aprovação; o envio recalcula a assinatura do MP4. **Recriar roteiro com a campanha atual** substitui a edição local anterior e exige nova revisão dos materiais e geração do MP4. A rotina também refaz dados desatualizados antes do primeiro upload. Vídeos com envio externo não podem ser substituídos localmente.

Pausar a campanha impede novas seleções e envios pelo sistema. Enquanto a rotina continua ativa, alterações ou revisão pendente podem reter um vídeo já enviado como privado na próxima consulta. Isso depende de conexão e resposta do Google: **confira e cancele agendamentos já enviados diretamente no YouTube Studio**. A pausa global interrompe as consultas locais e não cancela agendamentos remotos.

## Conferir a operação

Na versão 0.8, a rotina ativa redistribui **reservas locais vencidas** antes de selecionar novos produtos, mesmo com a fila cheia. Trabalhos automáticos locais autorizados, na fila ou prontos, recebem o próximo horário disponível, respeitando as reservas futuras e o limite diário. Reservas a até dez minutos do horário atual também podem ser movidas para dar margem ao envio. Roteiro, MP4, revisão editorial e contagem de tentativas de geração são preservados. O último horário anterior e a data do ajuste ficam registrados no calendário.

O limite diário considera a data de publicação confirmada dos vídeos automáticos quando ela está disponível, no horário de Brasília; não usa somente a antiga data planejada. Reservas locais vencidas não ocupam vagas futuras, enquanto envios externos sem confirmação continuam sendo tratados de forma conservadora. O sistema não conhece publicações feitas por fora dele e não garante um limite total para todo o canal.

Em **Calendário**, cada item distingue preparação manual, publicação planejada localmente, envio em andamento e agendamento confirmado no YouTube. Um agendamento cujo horário passou ainda depende de confirmação pública. A agenda usa os horários efetivamente configurados na rotina ou aprendidos com resultados suficientes; não apresenta sugestões iniciais como se fossem a configuração atual.

A recuperação não altera agendamentos já confirmados no destino, envios incertos, tentativas do Buffer, produtos/campanhas pausados ou vídeos manuais. Um upload privado com ID confirmado, ainda em processamento e sem agendamento confirmado, pode reservar um novo horário antes do primeiro pedido de agendamento. Esse ajuste permanece local até a API confirmar o agendamento; não cria outro upload. Reservas sem vaga nos próximos oito dias aguardam um ciclo futuro.

Na versão 0.7, a continuidade também cobre vídeos automáticos já prontos, antes de qualquer tentativa de envio:

- Mudanças no produto ou na campanha recolocam o vídeo local na produção. O trabalhador refaz o roteiro com os dados atuais e gera outro MP4. Edições manuais são preservadas e voltam para revisão; aprovações e verificações antigas são invalidadas.
- Um MP4 local ausente pode ser gerado novamente, mantendo o roteiro quando os dados continuam atuais. Registros com tentativa externa, inclusive resposta incerta, continuam exigindo conferência do destino. Uma retenção exclusivamente local do YouTube, sem ID ou tentativa de upload, pode voltar à produção.
- Com menos de 512 MB livres ou dependências ausentes, a geração espera sem consumir tentativas. Após corrigir a condição, o próximo ciclo pode continuar, respeitando pausas e autorizações.
- A pausa, a fonte, a autorização, o limite de três vídeos pendentes e a reserva de horários são conferidos novamente depois de criar o roteiro. Ciclos simultâneos não devem reservar a mesma vaga nem ultrapassar a fila.
- A consulta do YouTube ignora registros com erro definitivo, resposta incerta ou prazo de consulta futuro ao escolher o lote seguinte. Também ignora trabalho já encaminhado ao Buffer; não alterna o destino para repetir um envio.

O catálogo autorizado continua com intervalo normal de quatro horas. Falhas temporárias de rede ou da fonte usam esperas de 5, 15, 30, 60, 120 e depois até 240 minutos, salvas no banco. Arquivo inválido ou acesso recusado aguarda quatro horas. Uma consulta bem-sucedida zera a sequência de falhas. Os dados anteriores são preservados; itens sem confirmação por 24 horas continuam bloqueados para a rotina. Pausar, trocar a fonte ou importar um arquivo durante uma consulta impede que a resposta antiga substitua a escolha mais recente. O painel mostra tentativa, atualização aceita e próxima consulta; o horário é uma previsão enquanto o programa está aberto.

Essas retomadas dependem de **programa aberto**, computador ligado e permissões válidas. Reabrir preserva prazos; a versão 0.12 oferece início com Windows e operação em segundo plano, conforme a seção de continuidade. Campanhas com revisão manual, edição desatualizada, três falhas de geração ou envio externo incerto continuam pedindo sua intervenção. A fila total de três vídeos pendentes é mantida para limitar acúmulo, inclusive quando algum item exige atenção.

A página **Começar e acompanhar** mostra dependências de vídeo, espaço livre, produtos autorizados, acesso ao canal e o último teste local. Ela também mostra o próximo produto elegível, os horários em uso e publicações que aguardam resultados informados.

- **Testar vídeo e voz no notebook** cria um clipe real separado dos produtos e confere a decodificação. Não usa conta, não publica e não registra vendas. O resultado pode ser assistido no próprio painel. Sem voz pt-BR instalada, informa que o vídeo funciona sem narração. O teste evita execução simultânea e tem limites de duração; uma interrupção aparece como erro recuperável após reiniciar.
- **Verificar acesso ao YouTube** consulta a conta autorizada e confirma que ela acessa o canal selecionado. Essa consulta não cria publicações. O início da operação também verifica esse acesso antes de ativar a rotina. A aprovação de uma postagem específica só será conhecida quando ocorrer um envio real.
- **Retomar geração** reabre uma geração com erro após esgotar as tentativas locais. Exige os materiais autorizados e, para vídeos da rotina, a rotina e o produto ativos. Registros que já possuem tentativa de envio externo exigem conferência do destino e não são reenviados por esse botão.

A geração exige dependências disponíveis e pelo menos 512 MB de espaço livre. O teste salva somente o clipe, sua imagem e um relatório local; não cria produto nem publicação no banco.

## Aprendizado dos horários

Em **Resultados**, a operação também consulta contagens públicas de vídeos que o sistema confirmou como publicados no YouTube. Com conta conectada e rotina ativa, cada vídeo pode ser atualizado a cada seis horas, em lotes de até 20 por consulta. Conferimos o canal e a visibilidade pública antes de aceitar visualizações, curtidas ou comentários. A tabela mostra a data da leitura; dados ausentes não viram zero, e uma falha preserva a última contagem com aviso. Essa leitura não altera cliques, comissões nem marca resultados de afiliado como informados.

As métricas usam a mesma autorização Google e a [consulta oficial de vídeos](https://developers.google.com/youtube/data/reference/rest/v3/videos/list), sujeita à disponibilidade e cota da API. Contagens não comprovam atenção, cliques no link ou vendas. Leituras com falha aguardam pelo menos 15 minutos; a consulta não repete uploads. Desconectar o canal remove esse cache, e contagens automáticas com mais de 30 dias são descartadas quando o aplicativo volta a executar. A integração de métricas foi testada com respostas simuladas; a validação com publicações comerciais reais continua pendente.

Em **Modo automático → Como escolher os horários**, escolha horários fixos ou aprendizado pelos cliques registrados. Na configuração inicial recomendada, o aprendizado está habilitado e começa usando 18h. A mudança considera apenas resultados explicitamente salvos em **Registrar publicação**, com pelo menos três registros em cada um de dois horários. Publicações automáticas ainda sem resultados ficam como **não informadas** e não contam como zero cliques. Um zero que você registrar é uma observação válida.

Quando há base suficiente, a rotina prefere as horas com maior mediana de cliques, respeitando o limite diário e os horários já ocupados. Isso afeta os próximos agendamentos criados, sem mover publicações já agendadas. A comparação é um indício, não prova causal de que o horário produzirá mais vendas. Cliques e comissões continuam sendo informados por você. O intervalo por produto passa a contar da publicação real registrada, em vez da preparação antecipada do arquivo.

## Como a rotina funciona

Antes de começar cada geração automática, a fila confere novamente a autorização, as pausas do produto e da campanha, a disponibilidade do catálogo e a ausência de tentativa externa. Um item retido não impede a geração de outro elegível. Se os dados mudaram, um roteiro automático sem edição manual é refeito antes de renderizar; um roteiro editado ou manual é preservado e pede recriação explícita.

Ao reabrir o programa depois de uma interrupção, gerações automáticas locais podem ser retomadas quando a rotina e o produto estiverem autorizados. A primeira falha espera dois minutos; a segunda, dez; na terceira, o vídeo exige atenção. O contador não é zerado ao reiniciar. Vídeos manuais não são retomados automaticamente, e qualquer registro de tentativa externa impede essa recuperação. Em **Começar → Fila de produção**, confira retenções e próximas tentativas. Uma pausa não interrompe a codificação que já começou; impede novos inícios automáticos e envios locais posteriores, conforme as verificações do destino.

Uma trava do sistema operacional limita o uso a uma instância por pasta de dados, inclusive em portas diferentes. O modo normal e o tester usam pastas distintas e podem ser abertos juntos. A trava é liberada quando o processo termina; não apague o arquivo studio.lock para tentar forçar outra instância.

- Seleciona produtos autorizados. Primeiro experimenta os que ainda não têm resultados; depois usa comissões confirmadas informadas no histórico para ordenar os elegíveis. Alterna até quatro variações por produto, com sete dias de intervalo por padrão. Ao esgotar produtos ou versões, aguarda novos itens.
- Extrai até quatro características do cadastro, cria abertura, cenas e encerramento, escreve legenda com o link preservado e publicidade identificada. Não produz demonstrações físicas do produto nem depoimentos de uso.
- Renderiza de quatro a sete cenas com texto, movimento, transições, foto opcional e narração pt-BR do Windows quando disponível. Sem voz instalada, gera vídeo com texto e registra o aviso. Exporta MP4 H.264/AAC a 24 fps, legenda da publicação, SRT e metadados locais.
- O gerador local funciona sem modelo de IA. Se Ollama já estiver aberto com modelo local instalado, pode criar a pergunta inicial e sugerir a ordem das características. A aplicação não instala modelos, não inicia Ollama nem chama modelos pagos.
- Envia diretamente ao YouTube, inicialmente como privado, usando upload retomável. Confirma processamento e identificação nativa de publicidade antes de agendar a publicação. Só registra **publicado** quando a API informa visibilidade pública; registra a contagem de visualizações disponível nessa confirmação.
- Mantém o ID do vídeo e não cria um novo envio quando a resposta de um upload fica incerta. Nesse caso, confira o YouTube Studio e vincule o ID privado existente no painel. Falhas temporárias após criar a sessão são consultadas novamente após 15 minutos. A retomada usa a sessão persistida.
- Não acompanha comissões ou cliques automaticamente. Registre os valores confirmados pela plataforma e todos os custos em **Resultados** para medir o resultado dos valores registrados.

A integração depende de autorização, permissões, cotas e processamento do Google. O primeiro teste privado em canal real foi confirmado, incluindo processamento e propriedade do canal; o agendamento e a publicação pública comercial ainda precisam ser validados. O botão de iniciar permanece desabilitado enquanto faltarem produtos autorizados ou canal.

## Descoberta contínua por catálogo

Em **Começar → Seus produtos → Buscar novos produtos de um catálogo autorizado**, informe uma URL pública JSON da fonte autorizada. A consulta roda a cada quatro horas, importa novos itens, atualiza os existentes e pausa itens removidos ou inativos. Você também pode importar um arquivo inicial com o catálogo completo.

**Não existe busca universal automática em todas as lojas nesta versão.** A fonte precisa fornecer links emitidos para sua afiliação. A aplicação não converte uma URL de loja em link comissionado e não verifica sua aprovação ou atribuição da comissão. Sem uma fonte compatível, a seleção automática usa os produtos que você cadastrar e autorizar.

Formato da fonte (até 100 itens e 1 MB):

```json
{
  "products": [
    {
      "id": "codigo-estavel-do-produto",
      "name": "Nome confirmado",
      "description": "Características verificadas, com pelo menos 30 caracteres.",
      "affiliate_url": "https://seu-link-oficial-de-afiliado",
      "image_url": "https://sua-fonte-autorizada.example/foto-propria.jpg",
      "kind": "physical",
      "category": "Casa",
      "price": 120,
      "commission_percent": 10,
      "active": true
    }
  ]
}
```

`kind` aceita `physical` ou `digital`. `image_url` é opcional e só inicia downloads com a autorização específica de fotos. Preço e comissão são opcionais e informados pela fonte; não comprovam ganhos. Use um `id` estável por produto. O documento representa a lista completa atual, não apenas novos itens. Todos os itens são validados antes de alterar o banco. Exemplos não são importados para a operação real.

Produtos da fonte são retidos quando a última leitura tem mais de 24 horas. Pausas retêm o envio. Mudanças no link ou descrição antes do primeiro upload refazem o conteúdo e a renderização automaticamente. Se já houver envio remoto, a publicação é retida e vídeos agendados pelo sistema podem voltar a privado. Confira o painel em caso de alteração no catálogo. Com o programa fechado ou sem acesso à internet, não é possível cancelar agendamentos remotos. Produtos manuais dependem da sua manutenção.

Atualizar o catálogo preserva sua pausa, autorização e limite de variações de cada produto. A disponibilidade na fonte é conferida separadamente: um item removido, inativo ou desatualizado permanece retido mesmo se estiver autorizado na rotina. Produtos que versões anteriores já deixaram pausados precisam ser reativados no painel quando você quiser retomá-los.

## Pausar e acompanhar

**Pausar operação** interrompe novas ações locais, depois da ação já em andamento. Não cancela vídeos já agendados remotamente; confira o YouTube Studio para alterar essa agenda. Desconectar também não apaga vídeos do canal.

O calendário geral mostra preparação; a seção **Publicações no YouTube**, na página Começar, mostra envio, processamento, agendamento e confirmação pública. Problemas e atividade ficam registrados localmente. Um vídeo que já tem envio externo fica protegido contra edição local para não misturar arquivos e publicações diferentes.

## TikTok opcional

A integração anterior com Buffer continua disponível em **Modo automático** para rascunhos. Ela exige chave pessoal do Buffer, canal conectado e ponte de mídia cloudflared. Essa ponte não foi validada com envio real nesta instalação. Quando YouTube está habilitado, ele é o destino da rotina; não há distribuição simultânea para dois destinos.

A integração documentada do Buffer não expõe a identificação comercial nativa exigida no TikTok, então usa `saveToDraft: true`. Finalize a marcação e publicação no serviço que oferecer essa opção. A postagem pública automática de afiliados no TikTok permanece pendente, conforme sua escolha de manter custo zero. Fontes: [Buffer](https://developers.buffer.com/reference.html#tiktokpostmetadatainput), [TikTok](https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service).

## Dados e segurança

Banco, mídias e credenciais ficam em `data/`, ignorada pelo Git. Credenciais Google e Buffer são criptografadas com Windows DPAPI para o usuário atual. Não compartilhe essa pasta nem envie os JSONs de credenciais no chat. O arquivo OAuth original baixado fica onde você o salvou; o programa não o remove. Exportar dados pelo painel não inclui segredos ou sessões de upload.

A interface escuta apenas em 127.0.0.1, valida Host, origem e token nas alterações. Buscas públicas bloqueiam endereços privados e redirecionamentos para a rede local. O retorno OAuth não registra códigos de autorização no log. Faça backup da pasta `data/` com o programa fechado; restauração das credenciais requer o mesmo usuário Windows. Para outra máquina/usuário, reconecte as contas.

O campo legado `jobs.tiktok_url` do banco também armazena links confirmados do YouTube, para preservar compatibilidade com registros anteriores.

## Verificação

```powershell
python -m unittest discover -s tests -v
node --check web/app.js
node --check web/automation.js
node --check web/setup.js
```

Testes de publicação usam respostas simuladas, sem uploads em contas reais. Artefatos de QA e o vídeo demonstrativo ficam em `artifacts/`, separados de `data/`. Não representam vendas nem produtos reais de afiliado.
