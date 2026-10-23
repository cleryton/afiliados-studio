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

No notebook, três gerações reais também podem ser conferidas em uma instalação isolada: produção inicial, atualização da fonte e reposição de arquivo local ausente. Nenhuma delas comprova publicação ou venda. O programa precisa continuar aberto; não é instalado um serviço de inicialização do Windows.

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
