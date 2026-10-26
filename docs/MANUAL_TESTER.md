# Manual do usuário tester — Afiliados Studio

Versão 0.5.0-beta · atualizado em 18/10/2026.

Este roteiro permite testar instalação, roteiro, vídeo, narração, legendas e recuperação de falhas. O primeiro teste não exige conta de afiliado, Google, Buffer nem assinatura de IA.

## 1. O que preparar

- Notebook com Windows e Python 3.11 ou superior; a instalação foi verificada com Python 3.12. Execute instalar.bat novamente ao atualizar esta versão.
- Internet para instalar as duas dependências gratuitas. Depois, a demonstração local funciona sem conta externa.
- Pelo menos 512 MB livres para gerar os clipes. Separe espaço adicional se testar muitos vídeos.
- Uma pasta própria para o projeto. Extraia o ZIP antes de executar os arquivos.

Se o repositório for privado, o responsável precisa conceder acesso ao seu GitHub ou fornecer o ZIP do código. Não compartilhe sua senha para receber acesso.

## 2. Instalar e abrir o modo correto

1. No GitHub, use **Code → Download ZIP** ou receba o pacote do responsável.
2. Extraia a pasta. Não execute o programa de dentro do ZIP.
3. Abra **instalar.bat** e aguarde a mensagem de instalação concluída. Ele cria uma pasta `.venv` exclusiva do projeto e instala as dependências ali.
4. Abra **iniciar_tester.bat**.
5. O navegador deve abrir `http://127.0.0.1:8766`. Confira a faixa **MODO TESTER · PUBLICAÇÃO EXTERNA BLOQUEADA**.

Mantenha a janela do programa aberta. Para encerrar, volte a ela e pressione **Ctrl+C**.

| Modo | Como abrir | Endereço padrão | Dados | Publicação externa |
| --- | --- | --- | --- | --- |
| Tester | iniciar_tester.bat | porta 8766 | data-tester/ | Bloqueada |
| Normal | iniciar.bat | porta 8765 | data/ | Depende de autorização e ativação |

O modo tester sempre usa `data-tester`, mesmo que outra pasta de dados tenha sido configurada no ambiente. Abrir o tester não troca nem apaga o banco normal.

Se faltar Python, obtenha o instalador no [site oficial](https://www.python.org/downloads/windows/), marque a opção de adicioná-lo ao PATH e tente instalar novamente. Se a instalação falhar, envie a mensagem exibida ao responsável, após verificar que ela não contém informação pessoal.

## 3. Primeiro teste: vídeo e voz

1. Em **Começar e acompanhar**, encontre **Conferir a operação**.
2. Clique em **Testar vídeo e voz no notebook**.
3. O botão fica desabilitado e aparece a mensagem de teste em andamento.
4. Aguarde o resultado. Esse teste inclui imagem, voz quando disponível, criação do MP4 e verificação do arquivo.
5. Abra **Assistir ao teste local** e confira o clipe.

**Aprovado:** o vídeo reproduz, a imagem é legível e há narração em português. Sem voz portuguesa instalada, o resultado deve informar a ausência de narração; nesse caso, o vídeo com texto continua disponível. Registre essa condição no relatório do teste.

O clipe é local: não vira produto, publicação nem venda no banco.

## 4. Fluxo completo: do cadastro ao MP4

1. Volte a **Começar e acompanhar** no modo tester.
2. Clique em **Criar vídeo de demonstração**.
3. O sistema cria um cadastro ilustrativo, monta o roteiro e abre o **Estúdio de vídeos**.
4. Aguarde o cartão passar por fila e geração até ficar pronto. O tempo depende do notebook; mantenha o programa aberto.
5. Clique em **Ver vídeo e legenda** e reproduza o MP4.
6. Confira abertura, nome da demonstração, características e encerramento nas cenas.
7. Baixe **MP4**, **legenda do post** e **legendas SRT**.
8. Abra os arquivos baixados e confira se correspondem ao conteúdo mostrado.
9. Clique novamente em **Criar vídeo de demonstração**: enquanto houver uma demonstração não publicada no banco de teste, o sistema reutiliza esse trabalho e evita criar outro igual.

**Importante:** o endereço `example.com` é ilustrativo, não é uma oferta real e não paga comissão. A identificação “sem comissão” faz parte da demonstração. Nenhuma conexão de rede social será pedida nessa etapa.

## 5. Cadastro e edição manuais

No modo tester, você também pode cadastrar outro produto para verificar os formulários:

1. Abra **Produtos → Adicionar produto**.
2. Use um endereço de exemplo, como `https://example.com/produto-teste`.
3. Preencha nome, categoria e pelo menos 30 caracteres de descrição demonstrativa. Não use dados de clientes ou um link pessoal para este roteiro.
4. Salve o cadastro e clique em **Criar roteiro**.
5. Edite uma cena, salve e reabra para conferir a persistência.
6. Para gerar, confirme que revisou os dados e possui autorização para usar os materiais. Nos exemplos deste manual, use somente texto criado por você e imagens próprias, se quiser testar fotos.

**Ler link** depende da página pública. Falhar nessa leitura não impede preencher o cadastro manualmente. Para testar a rejeição de rede privada, use `http://127.0.0.1/` no formulário: ele deve mostrar erro e manter os campos disponíveis para correção.

## 6. Roteiro de validação

Marque **Passou**, **Falhou** ou **Não testado** para cada item.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T01 | Abrir iniciar_tester.bat | Porta 8766 e faixa de modo tester visível. |
| T02 | Executar o teste de vídeo e voz | Carregamento visível; MP4 reproduzível; narração ou aviso claro de ausência. |
| T03 | Criar a demonstração | Cadastro ilustrativo e trabalho no estúdio; sem conexão de contas. |
| T04 | Conferir o MP4 e os três downloads | Vídeo, legenda do post e SRT disponíveis. |
| T05 | Clicar novamente em criar demonstração | Reutiliza o trabalho ainda não publicado no banco de teste. |
| T06 | Editar e salvar um roteiro manual | Texto salvo reaparece ao reabrir. |
| T07 | Tentar um endereço de rede privada | Mensagem de erro e possibilidade de corrigir o formulário. |
| T08 | Fechar e abrir novamente o tester | Cadastros e vídeos locais preservados. |
| T09 | Consultar acesso/publicação no tester | Conexão de contas e envios externos bloqueados; não há postagem. |
| T10 | Abrir Manual e baixar diagnóstico | JSON disponível sem credenciais, conta, produtos ou links pessoais. |
| T11 | Reduzir a largura da janela | Navegação e ações utilizáveis, sem campos cortados. |

Não provoque falhas apagando arquivos ou desligando o notebook durante gravações. Se houver uma falha real de geração, o programa tenta recuperar a produção automática com limites. O botão **Retomar geração**, quando disponível, exige as autorizações e verifica se há tentativa de envio externo.

## 7. Relatar um problema

No topo do painel, abra **Manual** e clique em **Baixar diagnóstico sem credenciais**. O JSON inclui somente versão, sistema, disponibilidade de recursos, contagens de estados e resultado do teste local. Não inclui nomes de produtos, links de afiliado, canal, roteiros, mensagens de erro brutas, caminhos locais ou tokens.

Use este modelo:

```text
Versão do aplicativo:
Modo: tester / normal
Data e hora (Brasília):
Item do roteiro: T01, T02...
Passos para reproduzir:
Resultado esperado:
Resultado observado:
O problema acontece sempre ou às vezes?
Diagnóstico JSON anexado: sim / não
Imagem revisada para remover dados pessoais: sim / não / sem imagem
```

Revise o que compartilhar. Não envie senha, chave Buffer, arquivo OAuth, pasta `.venv`, pasta `data`, pasta `data-tester` ou exportação completa do banco. Reporte na área **Issues** do repositório, se disponível, ou ao responsável pelo teste; o programa não envia o diagnóstico automaticamente.

## 8. Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| “Python não encontrado” | Instale o Python e reabra o instalador. |
| Dependência ausente | Execute instalar.bat novamente com internet. |
| Porta ocupada | Confira se outra janela do programa já está aberta; use a instância existente ou encerre a janela antiga. |
| Sem narração | Confira se existe uma voz pt-BR nas configurações de fala do Windows; registre o aviso exibido. |
| Geração demorando | Mantenha o programa aberto; confira o estado no estúdio e eventuais erros. |
| Pouco espaço | Libere espaço sem apagar arquivos do aplicativo enquanto ele está em uso. |
| Google/Buffer bloqueado | Isso é esperado no modo tester. Não conecte contas para os testes locais. |
| Cadastros não aparecem no modo normal | Os bancos são separados; isso é esperado. |

## 9. Etapa posterior: publicação real

A validação de envio real deve ser combinada com o responsável pelo teste. Ela usa **iniciar.bat**, dados reais verificados, link de afiliado aprovado e autorização do canal Google. Consulte a configuração completa no [README](../README.md).

Ao ativar a operação normal, vídeos podem ser publicados publicamente no YouTube. Pausar a operação interrompe novas ações locais, mas não remove agendamentos que já estejam no YouTube. Confira a agenda no YouTube Studio.

A integração de postagem foi testada com respostas simuladas; o primeiro upload em uma conta real ainda precisa de validação. O TikTok continua como rascunho na integração atual. Cliques e comissões são informados pelo usuário, e nenhuma receita é garantida.

## 10. Testar campanhas e revisão (0.4)

1. Crie a demonstração local e aguarde o MP4 no estúdio.
2. Abra **Campanhas → Criar campanha**. Informe nome e público, escolha estilo e encerramento, marque **Exigir minha aprovação por vídeo** e selecione o produto demonstrativo. Salve.
3. Abra **Fila de revisão**. O vídeo antigo tem uma pendência de campanha. Clique **Recriar roteiro com a campanha atual**: isso substitui a edição anterior. Confira as cenas, autorize os materiais de demonstração e clique **Gerar MP4 agora**.
4. Quando terminar, confira que as verificações estão concluídas e o estado é **Aguardando aprovação**. Assista à prévia e aprove. O modo tester continuará bloqueando qualquer publicação externa.
5. Solicite ajustes: o vídeo deve ficar bloqueado. Aprovar novamente libera a revisão local quando todas as verificações passam.
6. Edite o roteiro, ou altere o público da campanha. A aprovação antiga não deve continuar válida. Recrie e gere novamente para aplicar a nova direção editorial.
7. Teste os filtros, inclusive um sem registros, e confira a navegação em uma janela estreita. No celular, role a faixa de ícones horizontalmente para acessar todos os destinos.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T12 | Criar campanha e vincular produto | Campanha persistida com os campos escolhidos. |
| T13 | Gerar vídeo com revisão manual | Verificações concluídas; aprovação pendente. |
| T14 | Aprovar e solicitar ajustes | Estados coerentes; no tester nenhum envio externo. |
| T15 | Mudar roteiro ou campanha | Aprovação anterior deixa de valer. |
| T16 | Verificar MP4 de versão anterior | Decodificação e conferência do arquivo ou erro com instrução de recuperação. |

O botão **Recriar roteiro** exige nova geração do vídeo e não serve para substituir arquivos já enviados ao YouTube. Pausar uma campanha não garante cancelar agendamentos no destino; essa conferência deve ser feita no YouTube Studio em uma validação real.

## 11. Testar a criação de conteúdo 0.5

Em **Modo automático → Criação de conteúdo**, selecione roteiro curto e voz ágil, salve e recrie um roteiro local de teste. Confira até duas características, público e estilo da campanha, link preservado e estimativa de duração. Depois de autorizar os materiais, gere e reproduza o MP4.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T17 | Usar roteiro curto com quatro características cadastradas | Até duas características por vídeo; variações podem usar as demais, sem inventar detalhes. |
| T18 | Recriar um roteiro de um produto já usado | Usa uma abertura alternativa quando ainda houver uma disponível para o contexto. |
| T19 | Gerar nos dois formatos | Capítulos visuais e identificação de publicidade legíveis; foto opcional preservada. |
| T20 | Baixar o SRT | Trechos de até duas linhas com tempos crescentes; temporização aproximada, não sincronização exata por palavra. |
| T21 | Editar uma cena | Estimativa de leitura atualizada e aprovação anterior invalidada. |
| T22 | Ler uma página pública com um único produto em JSON-LD | Nome e características explícitas sugeridos, com origem informada; revise antes de salvar. Página bloqueada ou sem dados permite preenchimento manual, preservando seu link. |

Sem uma voz pt-BR instalada, o vídeo continua com texto e o aviso de ausência de narração. A mudança de ritmo só afeta a voz quando ela está disponível. O modo tester mantém todo envio externo bloqueado.

## 12. Testar vídeo e continuidade da operação (0.6)

Escolha **Modo automático → Texto na tela → Trechos curtos**, salve, recrie um roteiro de teste e gere novamente. Assista a uma cena longa: o texto deve mudar durante a cena, preservando a sequência do roteiro. O tempo é aproximado, sem alinhamento exato por palavra. Compare com **Cena completa** em um segundo roteiro. Abra **Começar → Fila de produção** para conferir os estados reais e motivos de retenção.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T23 | Gerar trecho longo nos dois formatos | O texto muda dentro do MP4, sem perder palavras; SRT e metadados correspondem ao roteiro. |
| T24 | Pausar um produto automático antes de ele começar | A fila o retém e mostra o motivo; outro trabalho elegível pode continuar. |
| T25 | Alterar dados da fonte antes de renderizar | Roteiro automático sem edição é atualizado; edição manual é preservada e pede recriação. |
| T26 | Fechar durante uma geração automática local e reabrir | Retomada programada com espera de 2 ou 10 minutos; após três falhas, exige atenção. |
| T27 | Interromper um vídeo manual | Fica com erro recuperável; não é retomado por conta própria. |
| T28 | Abrir o mesmo modo duas vezes | Segunda instância rejeitada antes de tocar no banco; a primeira continua operando. |
| T29 | Encerrar e reabrir normalmente | Trava liberada pelo sistema operacional; dados preservados. |

T24–T26 exigem produtos de teste autorizados na rotina local. O modo tester bloqueia publicações mesmo com a geração automática ativa. Não use contas reais. Tentativas já enviadas a um destino externo nunca fazem parte da recuperação automática. Não é necessário provocar três falhas no notebook: essa condição também é coberta pelos testes automatizados.

## 13. Métricas do YouTube (0.6)

O modo tester não consulta métricas externas. Em **Resultados**, confira que cliques e comissões ainda não informados não aparecem como zeros confirmados. Na operação real, a leitura de visualizações, curtidas e comentários exige canal conectado e rotina ativa; somente vídeos confirmados como publicados pelo sistema são consultados. Ela não identifica cliques de afiliado nem vendas.

Em um teste posterior com conta real autorizada, confira a data de leitura na tabela e compare com o YouTube Studio, considerando o atraso de atualização da API. Não é necessário esperar seis horas para validar respostas ausentes ou falhas: os testes automatizados cobrem esses casos com respostas simuladas. Uma falha não deve apagar a última contagem nem alterar cliques e comissões. Desconectar remove o cache de métricas. Sem conta real, a integração continua pendente de validação externa.

## 14. Continuidade automática (0.7)

Use somente produtos de demonstração no modo tester. A rotina precisa estar ativa e o produto autorizado. Vídeos criados manualmente não são convertidos em trabalhos automáticos. Ao terminar, pause a rotina. Não remova arquivos de produtos reais para provocar falhas.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T30 | Atualizar um produto de catálogo depois de o vídeo automático ficar pronto | Sem tentativa externa ou edição manual, volta à produção e gera conteúdo com os dados atuais, preservando o link. |
| T31 | Fazer o mesmo com roteiro editado manualmente | Edição mantida; volta a rascunho e pede revisão/recriação, sem substituição silenciosa. |
| T32 | Pausar produto ou campanha antes da atualização | Vídeo preservado e geração retida até reativar; o recomeço confere os dados atuais. |
| T33 | Conferir a fila em condições de espaço insuficiente | Mensagem sobre 512 MB livres, sem gastar tentativas; não é necessário encher o disco para testar. |
| T34 | Conferir atualização do catálogo em Começar, no modo normal de uma instalação de teste | Diferencia consulta pausada, última tentativa, dados aceitos e próxima consulta prevista. Sem confirmação, não mostra atualização bem-sucedida. |

A suíte automatizada cobre falta de espaço, MP4 ausente, duas criações simultâneas, pausa durante criação e troca de fonte durante consulta. A recuperação de um arquivo ausente mantém o roteiro atual, mas exige nova revisão se a campanha assim determinar. Falhas temporárias do catálogo aguardam 5, 15, 30, 60, 120 e até 240 minutos; erro de arquivo ou acesso recusado aguarda quatro horas. Não é preciso desligar a internet nem esperar horas para validar esses casos: os testes usam respostas controladas e relógio simulado.

No notebook, três gerações reais também podem ser conferidas em uma instalação isolada: produção inicial, atualização da fonte e reposição de arquivo local ausente. Nenhuma delas comprova publicação ou venda. O programa precisa continuar executando; consulte a seção 19 para o início com Windows da versão 0.12.

## 15. Agenda e retomada após ficar offline (0.8)

Abra **Calendário**. Um vídeo manual mostra **Preparação do vídeo**. Um vídeo da rotina, antes de qualquer envio, mostra **Publicação planejada**: isso ainda não é confirmação de agendamento ou publicação. A agenda deve mostrar os horários salvos na rotina, inclusive quando eles diferem da sugestão inicial.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T35 | Observar um trabalho automático com horário vencido, com rotina ativa e produto autorizado | Recebe uma nova reserva local; calendário mostra data anterior e data do ajuste. Não cria outro roteiro nem outro upload. |
| T36 | Pausar a rotina, o produto ou a campanha antes da retomada | Data preservada até a condição ser corrigida; não ignora pausas nem materiais sem autorização. |
| T37 | Conferir vídeo manual e vídeo da rotina no calendário | Preparação manual e intenção de publicação têm rótulos diferentes. |
| T38 | Conferir uma reserva ajustada | Nova data visível, roteiro mantido e explicação de que o destino ainda precisa confirmar. |
| T39 | Conferir agenda em 390 px de largura | Nome, datas, motivo e ações continuam legíveis sem alargar a página. |

Os testes automatizados usam relógio controlado para conferir vários horários vencidos, mudança de dia em Brasília, reserva simultânea, limite diário por publicação confirmada e reinício sem repetir ajustes. Não é necessário alterar o relógio do Windows. Testes de agendamento confirmado e ID privado usam respostas simuladas; o modo tester não publica. Em operação real, um agendamento externo confirmado deve continuar sendo gerenciado e cancelado no destino.

## 16. Fotos autorizadas do catálogo (0.9)

O modo tester **não baixa fotos externas**, mesmo com autorização salva. Para conferir fotos sem rede, adicione uma imagem própria no cadastro e gere uma demonstração. A prévia com uma ilustração deve ser identificada como ilustração; não representa teste físico do produto.

Em uma instalação de desenvolvimento isolada, no modo normal e sem conectar contas de publicação, é possível testar o catálogo com `image_url` apontando para uma foto própria em endereço público. Marque a opção específica para baixar e usar as fotos. Um link de exemplo sem autorização não deve ser usado como se fosse uma foto real.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T40 | Importar catálogo com `image_url`, sem autorização de fotos | Produto importado; nenhum download de foto. |
| T41 | Autorizar uma foto própria válida no ambiente isolado | JPEG local disponível no produto e na próxima geração, com link de afiliado preservado. |
| T42 | Conferir produto que já possui foto manual | Foto manual mantida; a fonte não a substitui. |
| T43 | Retirar autorização ou mudar endereço da foto | Foto gerenciada anterior desassociada; resposta antiga não altera a escolha nova. |
| T44 | Fonte sem foto válida | Pendência/falha com nova tentativa programada; vídeo ainda pode ser criado com texto. |
| T45 | Conferir painel em tela estreita | Nomes, estado e mensagens legíveis; nenhum download no modo tester. |

A suíte cobre arquivo inválido, resolução, tamanho, endereço privado, resposta lenta, falha de rede, concorrência, falta de espaço e retirada de autorização durante a leitura. Não é necessário encher o disco, usar URLs privadas nem interromper a internet do notebook para provocar esses casos. As fotos de teste são geradas localmente ou usam respostas controladas. A validação não comprova direitos autorais nem vendas.

## 17. Operação contínua e cópias locais (0.10)

Abra **iniciar_tester.bat** e mantenha a janela do programa aberta. Em **Começar → Conferir a operação**, aguarde **Rotinas em segundo plano** e **Cópia local do banco**. A primeira cópia normalmente termina no primeiro minuto. Os testes e as cópias permanecem separados dos dados reais.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T46 | Abrir e aguardar o primeiro ciclo | Checklist diferencia início das rotinas e cópia verificada; não informa publicação. |
| T47 | Conferir a pasta data-tester/backups | Uma cópia SQLite; data de sucesso no painel. Reabrir no mesmo dia preserva a cópia sem criar outra desnecessária. |
| T48 | Encerrar com Ctrl+C e reabrir | Encerramento não dispara retomada; reabrir mantém cadastros e prazos. |
| T49 | Abrir o mesmo modo duas vezes | Segunda janela informa instância existente; não entra em ciclo de reinício nem modifica o banco aberto. |
| T50 | Conferir a tela estreita | As duas verificações novas e mensagens longas permanecem legíveis. |

A suíte automatizada cobre queda de um processo filho real e retomada, limite de cinco reinícios, Ctrl+C, falhas temporárias, ciclo demorado, sete cópias, falta de espaço e cópia durante uma transação ainda não confirmada. Não mate processos reais, não provoque corrupção nem encha o disco para conferir esses casos. Modo tester continua sem publicação e sem consultas externas de fotos ou métricas.

Cópias incluem links e dados privados. Não anexe o banco ou a pasta backups a Issues. Elas não incluem as credenciais separadas nem os vídeos. Restauração exige auxílio de desenvolvimento e conferência das publicações no destino; o aplicativo não restaura automaticamente. O modo tester continua em janela. O modo normal 0.12 também oferece execução em segundo plano e início com Windows, descritos na seção 19.

## 18. Validar o fluxo antes de obter afiliação (0.11)

Em **Começar → Teste completo antes da afiliação**, crie o vídeo de teste e assista à prévia. Esse clipe é próprio, identifica o teste e não divulga produtos. Não é necessário preencher link de afiliado nem cadastrar um produto. O modo tester continua bloqueando o envio externo.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T51 | Criar teste sem produtos ou contas | Vídeo e voz gerados localmente, com prévia; produtos e resultados comerciais permanecem vazios. |
| T52 | Clicar novamente ou reabrir | Mesmo teste persistido; nenhum vídeo ou upload adicional. |
| T53 | Usar modo tester | Preparação local disponível; nenhuma autorização de envio. |
| T54 | Pausar teste | Novos passos retidos; a produção comercial não é ativada. |
| T55 | Conferir tela estreita | Estados, botão de envio, pausa e mensagens cabem em 390 px. |

Em validação posterior **no modo normal**, o titular deve entrar no Google, configurar a credencial OAuth e autorizar o canal. Clique **Autorizar envio privado e iniciar**. Acompanhe preparação, envio e processamento; abrir a página do vídeo antes do processamento não representa teste concluído. Só aceite o resultado quando o painel confirmar que a API respondeu com vídeo processado, privado e pertencente ao canal esperado. Confira a visibilidade no YouTube Studio. Esse resultado não comprova postagem pública ou afiliação.

Não compartilhe senha, código de confirmação ou JSON OAuth. O teste tem pausa própria; uma requisição em andamento pode terminar como privada. Se aparecer envio incerto, confira o destino antes de qualquer intervenção. A suíte cobre troca de canal, arquivo alterado, falha de rede, retomada, resposta incerta e ausência de contas usando respostas simuladas; esses testes não substituem a primeira autorização e o envio em canal real.

## 19. Execução em segundo plano e início com Windows (0.12)

O modo normal aberto por **iniciar.bat** passa a funcionar sem uma janela de terminal aberta. Fechar o navegador não encerra a execução. **parar.bat** pede encerramento ao aplicativo local. Para investigar uma falha de abertura, use **iniciar_console.bat**. O modo tester continua separado e em janela, com publicações bloqueadas.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T56 | Abrir iniciar.bat duas vezes | Uma instância saudável reaproveitada, com dados preservados. |
| T57 | Fechar a página e abrir novamente | Programa continua respondendo e mantém a fila. |
| T58 | Executar parar.bat | Encerramento normal, sem reinício pelo supervisor; outros aplicativos Python não são encerrados. |
| T59 | Executar ativar_inicio_windows.bat | Entrada de início automático do usuário atual configurada para esta instalação. Confira no checklist; não reinicie o Windows durante trabalhos reais. |
| T60 | Executar desativar_inicio_windows.bat | Somente a entrada desta instalação é retirada. A execução atual continua até usar parar.bat. |
| T61 | Abrir teste privado pronto, com credencial importada e sem canal conectado | Botão Conectar e testar em privado explica o único envio privado após consentimento. |

T59 e T60 alteram uma configuração real da conta Windows. Execute somente se deseja esse comportamento nesta instalação; não são obrigatórios para testar a criação de vídeos. A suíte automatizada usa um registro simulado para conferir instalação, retirada e preservação de outra instalação.

Os logs locais são limitados a dois arquivos de até 2 MB em data. Eles são privados e não fazem parte do diagnóstico para compartilhar. A suíte também verifica a rotação com um processo filho real.

Uma autorização Google pendente pode continuar após reiniciar o aplicativo dentro de dez minutos, com o pedido protegido pelo Windows. Ela só é consumida uma vez; uma tentativa nova substitui a anterior. Não é necessário provocar falha durante um consentimento real: estado incorreto, expiração, troca de tentativa e retomada são testados com respostas controladas.

**Conectar e testar em privado** pede somente o envio do clipe demonstrativo já pronto. Não ativa a rotina pública nem cria ofertas comerciais. Conectar pela etapa 02 continua disponível sem iniciar teste. Login, revisão das permissões e consentimento do canal são realizados pelo titular no navegador padrão.

## 20. Primeiro envio comercial sem esperar o horário (0.13)

O teste privado e a demonstração não são uma oferta com comissão. Para validar o fluxo comercial no modo normal, é preciso ter afiliação aprovada, link próprio e autorização dos dados e materiais do produto. O cadastro e os termos do programa são concluídos pessoalmente pelo titular.

Com produto autorizado e operação pública ativa, aguarde o vídeo ficar pronto, assista na Fila de revisão e use **Publicar agora no YouTube**. O clique pede a publicação pública desse vídeo após processamento, identificação comercial e verificações. Não adianta nem cancela outros agendamentos. “Solicitada” ou “aguardando confirmação” não significa publicado.

| ID | Ação | Resultado esperado |
| --- | --- | --- |
| T62 | Abrir vídeo automático pronto no tester | Aviso de publicação externa bloqueada, sem botão de publicar. |
| T63 | Conferir vídeo pronto com rotina pública pausada | Link para iniciar a operação; nenhum envio ao clicar apenas na navegação. |
| T64 | Solicitar envio imediato no modo normal autorizado | Pedido persistido para aquele vídeo e canal; estado solicitado até a confirmação pública. |
| T65 | Clicar de novo ou reabrir durante o pedido | Mesmo pedido e mesmo upload, sem duplicar publicação. |
| T66 | Conferir tela de 390 px | Explicação, estado e botão legíveis, com foco visível. |

T64 tem efeito real e só deve ser executado em um canal autorizado para publicação pública. A suíte usa respostas simuladas para testar visibilidade, identificação comercial, expiração, troca de canal, roteiro alterado e perda da resposta. Não provoque falhas de rede em um upload real. Se a API não confirmar visibilidade pública, confira o vídeo no YouTube Studio; o aplicativo não trata a ausência de confirmação como sucesso.

Retornos antigos de autorização Google não devem marcar um canal já conectado como expirado. “Verificar acesso ao YouTube” consulta o acesso real, sem publicar nem desconectar a conta.

## 21. Começar pela Kiwify

Na etapa 01 de Começar, **Abrir Kiwify** leva ao login oficial. O titular conclui pessoalmente o cadastro, o aceite dos termos e a validação solicitada. No painel da Kiwify, use **Marketplace** para encontrar produtos e solicitar afiliação. A aprovação depende do produtor.

A afiliação pode aparecer ativa antes de o cadastro estar completo. Se a aba Links pedir completar o cadastro, o titular precisa concluir essa etapa na Kiwify para liberar os links.

Depois da aprovação e do cadastro completo, use **Produtos → Minhas afiliações → Links** e cadastre seu link no estúdio com as características verificadas do produto. Convites de afiliação, links de outras pessoas e exemplos não são o seu link de divulgação. A identificação da plataforma Kiwify no cadastro não comprova aprovação ou atribuição de comissão.

No modo tester, use somente os exemplos locais; não conclua afiliações nem envios reais para testar esse atalho. A geração e o envio ao YouTube continuam sujeitos às verificações já descritas no manual.

## 22. Piloto de histórias para TikTok

Abra **Histórias no TikTok**. Confira o aviso de TikTok não conectado, as imagens previamente geradas e o botão **Preparar os três episódios**. Clique uma vez; cliques repetidos devem manter uma única temporada com episódios 1, 2 e 3. Aguarde a fila local e assista às prévias. O terceiro episódio tem desfecho.

Confira formato 720 × 1280, rótulos de ficção e IA, aparência consistente da protagonista, narração e os downloads MP4/SRT/legenda. O texto da legenda é fictício e não deve apresentar depoimentos ou comissões reais. A indicação no vídeo não substitui a configuração nativa de IA no TikTok. Ausência de voz portuguesa deve ser informada.

Durante reprodução, a atualização não deve reiniciar o vídeo. Erros permitem tentar gerar somente o episódio afetado. Fechar e reabrir durante geração deve retomar a fila, preservando episódios prontos. Não faça publicações reais em contas pessoais para testar a tela: esta área apenas gera arquivos locais e permanece separada das automações de afiliados. Veja também [TIKTOK.md](TIKTOK.md).

### Oferta nos episódios

No tester, autorize um produto demonstrativo com link ilustrativo. Aplique-o à minissérie e confira a remontagem: ficção preservada, publicidade visível desde o início e bloco comercial final sem atores ou depoimentos. A legenda deve conter exatamente o link cadastrado e explicar a possível comissão. Reaplicar a mesma oferta não deve recriar a temporada. Produto alterado ou autorização retirada deve sinalizar oferta desatualizada e ocultar os downloads da versão antiga na tela.

O campo de perfil aceita somente um @ válido. Salvar um @ não deve informar conta conectada nem publicar. Durante geração, editar o formulário não deve apagar o que está digitando. As marcações nativas de publicidade e IA são verificações do envio real, fora deste teste local.


## 23. Montagem com cortes e movimento

Em um episódio pronto, clique em **Remontar com cortes e movimento**. Deve entrar na fila uma única vez, sem criar outro episódio ou modificar o TikTok. Durante a montagem, o botão e a prévia ficam indisponíveis. A versão anterior fica em disco até a substituição do MP4 validado.

Assista ao arquivo novo: tomadas de até quatro segundos, planos gerais e reações, chave girando, carta deslizando do envelope, fotografia se movendo e abertura de porta nas cenas correspondentes. As legendas devem ficar estáveis e suas trocas não devem reiniciar a câmera. Os personagens continuam em imagens; não avaliar como animação corporal ou sincronização labial. Confira narração inteligível e efeitos suaves.

Confira a publicidade e o link de afiliado preservados, o formato vertical e o registro da montagem em roteiro.json. Para testar clipes próprios, use somente um padrão sintético ou material autorizado no ambiente tester e siga [CENAS_EM_MOVIMENTO.md](CENAS_EM_MOVIMENTO.md). Alterar o arquivo sem atualizar sua autorização deve interromper a montagem e preservar o MP4 anterior. Nenhum destes testes publica em redes sociais.


## 24. Prévia de animação 3D

Antes de gerar, a tela não deve declarar um vídeo 3D pronto. Depois de uma geração completa, confira a seção Novo · Animação 3D em 1440 e 390 px, o botão de download com foco visível e a reprodução sem reiniciar durante atualizações. A prévia deve apresentar personagens com volume, braços e cabeça em movimento, gestos e porta articulada. Não avaliar como caminhada ou sincronização labial precisa, que não estão implementadas.

Os episódios antigos continuam separados e nenhum envio externo ocorre. Com oferta demonstrativa no tester, conferir publicidade separada, link ilustrativo preservado e ausência de depoimentos. Arquivo incompleto ou produto com autorização retirada não deve produzir uma prévia pronta no painel. Geração 3D é opcional e exige Blender; veja ANIMACAO_3D.md.


## 25. Fila opcional de postagem TikTok

No tester, o formulário de conexão e os endpoints de conexão, ativação e fila externa devem estar bloqueados. Não use chaves reais para testar. O painel distingue conexão cadastrada, rotina pausada, agenda local e resposta do destino. Confira 1440 e 390 px, foco do link `?setup=publishing#stories`, entrada de senha protegida e preservação do formulário durante a atualização. A chave deve ser apagada do campo após uma tentativa de conexão, inclusive com erro.

A suíte simula perda de resposta, troca da identificação estável da conta, legenda e vídeo modificados, envio como rascunho, aviso de IA/publicidade, cota e restrição de plano. Nenhum desses testes publica. A confirmação real exige provedor e canal autorizados e link retornado para o perfil esperado. Veja POSTAGEM_TIKTOK.md.

## Conteúdo e resultados (0.18)

Consulte [o roteiro de teste de engajamento](ENGAJAMENTO_TIKTOK.md): métricas locais com desconhecidos distintos de zero, validação do perfil e da data, persistência e prévia do capítulo 2 em 3D. Nenhuma sugestão editorial comprova aumento de alcance.

## Biblioteca e limpeza (0.19)

Confira [Biblioteca e operação](BIBLIOTECA_E_OPERACAO.md): múltiplos capítulos 3D, preservação dos arquivos atuais e dos registros de postagem, remoção idempotente e distinção entre horário agendado e publicação confirmada.

## Semana e pacotes (0.20)

Veja [Semana de histórias](SEMANA_DE_HISTORIAS.md). Teste sete datas em São Paulo, reaproveitamento dos capítulos já prontos, processo único, parada em erro e recuperação sem duplicação. Pacotes desatualizados, alterados ou destinados a outro perfil devem ser recusados.
