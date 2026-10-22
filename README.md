# Afiliados Studio

[![Validadores](https://github.com/cleryton/afiliados-studio/actions/workflows/validate.yml/badge.svg)](https://github.com/cleryton/afiliados-studio/actions/workflows/validate.yml)

Aplicativo local para Windows. Cria roteiros, vídeos com narração e legendas, e integra o envio e agendamento ao YouTube pela API oficial. Sem assinatura de IA ou hospedagem. Energia e internet continuam sendo custos da operação.

Requer Python 3.11 ou superior (recomendado 3.12). Ao atualizar para 0.5, execute **instalar.bat** novamente para instalar as dependências corrigidas. Se houver um ambiente `.venv` com Python antigo, o instalador explica como recriá-lo sem apagar `data` e `data-tester`.

**Situação atual:** versão 0.5.0-beta. A criação local foi validada com MP4 real; a integração YouTube foi implementada e testada com respostas simuladas. O primeiro envio em um canal real ainda precisa de validação com afiliação aprovada e canal autorizado. Lucro não é garantido. O sistema não cria contas, não aceita contratos em seu nome nem inventa links que pagam comissão.

## Entrega para testers

Comece por [docs/MANUAL_TESTER.md](docs/MANUAL_TESTER.md). Execute **instalar.bat** uma vez e depois **iniciar_tester.bat**. Esse modo usa um banco separado em data-tester e bloqueia contas e envios externos. Uma demonstração completa pode ser criada pelo painel, sem afiliado ou Google. O manual também está no link Manual no topo da aplicação.

Para relatar falhas, use **Manual → Baixar diagnóstico sem credenciais** e o formulário de Issues do repositório. As verificações rodam automaticamente no GitHub a cada push e pull request: testes Windows, sintaxe, privacidade, pacote, Ruff, Gitleaks e auditoria de dependências. Consulte [docs/VALIDACAO.md](docs/VALIDACAO.md). Em um clone Git, **validar.bat** executa as verificações locais e os testes sem abrir o aplicativo.

## Abrir

Dê dois cliques em `iniciar.bat` ou execute:

```powershell
python -m pip install -r requirements.txt
python app.py --open
```

Abra http://127.0.0.1:8765/#start. Mantenha o programa aberto e o notebook ligado, com internet. A rotina impede suspensão automática enquanto está ativa, sem modificar permanentemente o plano de energia. Fechar a tampa pode suspender o notebook conforme a configuração do Windows.

## Configuração inicial

1. Crie sua conta num programa de afiliados, obtenha aprovação e gere ao menos um link de afiliado seu. O painel tem acesso ao programa da Hotmart; links físicos e digitais de outras plataformas também podem ser cadastrados.
2. Em **Começar e acompanhar**, adicione o produto, as características verificadas e uma foto autorizada opcional. Clique **Autorizar** para permitir o uso desses dados nas variações automáticas.
3. No [Google Cloud](https://console.cloud.google.com/apis/library/youtube.googleapis.com), crie um projeto e habilite **YouTube Data API v3**. Configure o consentimento OAuth e o público externo com seu e-mail como usuário de teste. Crie uma credencial OAuth do tipo **Aplicativo para computador** e baixe o JSON. Não é uma chave de API comum nem credencial de aplicativo Web.
4. Selecione o JSON no campo local do painel e clique **Salvar configuração Google**. Depois clique **Autorizar meu canal no Google** e conclua o consentimento na conta que possui seu canal. O programa usa retorno HTTP apenas no endereço de loopback local e PKCE; não pede senha Google.
5. Ative os [recursos avançados do canal](https://support.google.com/youtube/answer/13748639?hl=pt-BR) para disponibilizar links externos clicáveis nas descrições. O formato padrão é horizontal, 1280 × 720, para publicar como vídeo comum; links nas descrições de Shorts não são clicáveis.
6. Clique **Iniciar criação e publicação automática**. A publicação será pública no canal conectado. No primeiro início, a rotina começa em até um minuto: prepara um vídeo por dia às 18h de Brasília, com antecedência de até três vídeos. Ao retomar, mantém seus ajustes de ritmo e geração. O horário é um ponto inicial de teste, sem evidência de que seja o melhor para seu público. Ajustes ficam em **Modo automático**.

Projetos OAuth externos com status **Testing** recebem refresh tokens que expiram em 7 dias para este escopo. Reconecte quando solicitado. Para operação contínua, configure o status do aplicativo no Google conforme as exigências aplicáveis; sair do modo de teste e verificações são gerenciados no Google Cloud. Documentação: [expiração de tokens](https://developers.google.com/identity/protocols/oauth2#expiration), [autorização para aplicativos desktop](https://developers.google.com/identity/protocols/oauth2/native-app), [envio de vídeos](https://developers.google.com/youtube/v3/docs/videos/insert).

## Criação de conteúdo 0.5

Em **Modo automático → Criação de conteúdo**, escolha roteiro **Completo** (até quatro características) ou **Curto** (até duas por vídeo), formato e ritmo da voz. O modo curto alterna os detalhes entre variações. As aberturas consideram nome do produto, estilo e público da campanha; a criação procura uma alternativa quando a abertura já aparece no histórico daquele produto.

Os dados continuam vindo do cadastro: informe características específicas e confirmadas, como material, medidas, compatibilidade ou conteúdo incluído. O gerador não acrescenta experiência de uso, resultados, descontos ou benefícios que não tenham sido informados. A leitura do link depende do que a página pública oferece; revise os dados sugeridos.

Na leitura do link, o sistema tenta identificar um único [produto em JSON-LD](https://schema.org/Product) e aproveitar descrição, material, cor, tamanho, modelo e características adicionais explícitas. Sem esse formato, usa título e descrição HTML. Listas ambíguas não combinam características de produtos diferentes. Não executa scripts da loja, não baixa fotos automaticamente e não infere comissão ou aprovação da afiliação. O link original é mantido.

Cada vídeo tem capítulos visuais, identificação de publicidade e encerramento. Uma foto autorizada aparece em um painel com contraste; sem foto, usa tipografia e numeração de cenas. Hashtags seguem o tipo e a categoria cadastrados. A estimativa de tempo no editor é uma previsão de leitura, não um limite garantido; a duração real é medida na verificação do MP4.

A narração usa a voz pt-BR instalada no Windows, em ritmo natural ou ágil. O SRT divide o texto em trechos de até duas linhas, com temporização aproximada calculada a partir do texto e da duração das cenas; não é alinhamento exato palavra por palavra. A legenda do post mantém o link e a identificação de publicidade.

As configurações valem para novos roteiros. Para aplicá-las a um vídeo local existente, use **Recriar roteiro com a campanha atual**, revise e gere o MP4 novamente. Isso substitui a edição local anterior e invalida a aprovação. Vídeos com tentativa de envio externo permanecem protegidos contra substituição local.

## Campanhas e revisão editorial

Em **Campanhas**, defina o público ou contexto, o estilo da abertura e o encerramento. Vincule produtos e escolha se o sistema pode continuar após as verificações ou se exige aprovação de cada vídeo. Um produto pertence a uma campanha por vez. Produtos sem campanha continuam com a configuração padrão. A campanha não aprova sua afiliação nem substitui a autorização dos materiais.

A **Fila de revisão** reúne prévia, estado real e verificações: roteiro, link preservado, publicidade, autorização, dados atuais, campanha ativa e MP4. Cada nova renderização decodifica o arquivo e confere dimensões e duração. Arquivos de versões anteriores podem ser conferidos em **Verificar arquivo**. Isso confere a consistência técnica e os dados cadastrados; não avalia a veracidade de todas as alegações nem prevê vendas.

Na revisão manual, clique **Aprovar vídeo** depois de assistir. **Solicitar ajustes** bloqueia a continuidade. Mudar roteiro, produto, campanha ou arquivo invalida a aprovação; o envio recalcula a assinatura do MP4. **Recriar roteiro com a campanha atual** substitui a edição local anterior e exige nova revisão dos materiais e geração do MP4. A rotina também refaz dados desatualizados antes do primeiro upload. Vídeos com envio externo não podem ser substituídos localmente.

Pausar a campanha impede novas seleções e envios pelo sistema. Enquanto a rotina continua ativa, alterações ou revisão pendente podem reter um vídeo já enviado como privado na próxima consulta. Isso depende de conexão e resposta do Google: **confira e cancele agendamentos já enviados diretamente no YouTube Studio**. A pausa global interrompe as consultas locais e não cancela agendamentos remotos.

## Conferir a operação

A página **Começar e acompanhar** mostra dependências de vídeo, espaço livre, produtos autorizados, acesso ao canal e o último teste local. Ela também mostra o próximo produto elegível, os horários em uso e publicações que aguardam resultados informados.

- **Testar vídeo e voz no notebook** cria um clipe real separado dos produtos e confere a decodificação. Não usa conta, não publica e não registra vendas. O resultado pode ser assistido no próprio painel. Sem voz pt-BR instalada, informa que o vídeo funciona sem narração. O teste evita execução simultânea e tem limites de duração; uma interrupção aparece como erro recuperável após reiniciar.
- **Verificar acesso ao YouTube** consulta a conta autorizada e confirma que ela acessa o canal selecionado. Essa consulta não cria publicações. O início da operação também verifica esse acesso antes de ativar a rotina. A aprovação de uma postagem específica só será conhecida quando ocorrer um envio real.
- **Retomar geração** reabre uma geração com erro após esgotar as tentativas locais. Exige os materiais autorizados e, para vídeos da rotina, a rotina e o produto ativos. Registros que já possuem tentativa de envio externo exigem conferência do destino e não são reenviados por esse botão.

A geração exige dependências disponíveis e pelo menos 512 MB de espaço livre. O teste salva somente o clipe, sua imagem e um relatório local; não cria produto nem publicação no banco.

## Aprendizado dos horários

Em **Modo automático → Como escolher os horários**, escolha horários fixos ou aprendizado pelos cliques registrados. Na configuração inicial recomendada, o aprendizado está habilitado e começa usando 18h. A mudança considera apenas resultados explicitamente salvos em **Registrar publicação**, com pelo menos três registros em cada um de dois horários. Publicações automáticas ainda sem resultados ficam como **não informadas** e não contam como zero cliques. Um zero que você registrar é uma observação válida.

Quando há base suficiente, a rotina prefere as horas com maior mediana de cliques, respeitando o limite diário e os horários já ocupados. Isso afeta os próximos agendamentos criados, sem mover publicações já agendadas. A comparação é um indício, não prova causal de que o horário produzirá mais vendas. Cliques e comissões continuam sendo informados por você. O intervalo por produto passa a contar da publicação real registrada, em vez da preparação antecipada do arquivo.

## Como a rotina funciona

- Seleciona produtos autorizados. Primeiro experimenta os que ainda não têm resultados; depois usa comissões confirmadas informadas no histórico para ordenar os elegíveis. Alterna até quatro variações por produto, com sete dias de intervalo por padrão. Ao esgotar produtos ou versões, aguarda novos itens.
- Extrai até quatro características do cadastro, cria abertura, cenas e encerramento, escreve legenda com o link preservado e publicidade identificada. Não produz demonstrações físicas do produto nem depoimentos de uso.
- Renderiza de quatro a sete cenas com texto, movimento, transições, foto opcional e narração pt-BR do Windows quando disponível. Sem voz instalada, gera vídeo com texto e registra o aviso. Exporta MP4 H.264/AAC a 24 fps, legenda da publicação, SRT e metadados locais.
- O gerador local funciona sem modelo de IA. Se Ollama já estiver aberto com modelo local instalado, pode criar a pergunta inicial e sugerir a ordem das características. A aplicação não instala modelos, não inicia Ollama nem chama modelos pagos.
- Envia diretamente ao YouTube, inicialmente como privado, usando upload retomável. Confirma processamento e identificação nativa de publicidade antes de agendar a publicação. Só registra **publicado** quando a API informa visibilidade pública; registra a contagem de visualizações disponível nessa confirmação.
- Mantém o ID do vídeo e não cria um novo envio quando a resposta de um upload fica incerta. Nesse caso, confira o YouTube Studio e vincule o ID privado existente no painel. Falhas temporárias após criar a sessão são consultadas novamente após 15 minutos. A retomada usa a sessão persistida.
- Não acompanha comissões ou cliques automaticamente. Registre os valores confirmados pela plataforma e todos os custos em **Resultados** para medir o resultado dos valores registrados.

A integração depende de autorização, permissões, cotas e processamento do Google. Não foi validada com um canal real nesta instalação, pois ele ainda não está conectado. O botão de iniciar permanece desabilitado enquanto faltarem produtos autorizados ou canal.

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
      "kind": "physical",
      "category": "Casa",
      "price": 120,
      "commission_percent": 10,
      "active": true
    }
  ]
}
```

`kind` aceita `physical` ou `digital`. Preço e comissão são opcionais e informados pela fonte; não comprovam ganhos. Use um `id` estável por produto. O documento representa a lista completa atual, não apenas novos itens. Todos os itens são validados antes de alterar o banco. Exemplos não são importados para a operação real.

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
