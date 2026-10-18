# Manual do usuário tester — Afiliados Studio

Versão 0.3.0-tester · atualizado em 18/10/2026.

Este roteiro permite testar instalação, roteiro, vídeo, narração, legendas e recuperação de falhas. O primeiro teste não exige conta de afiliado, Google, Buffer nem assinatura de IA.

## 1. O que preparar

- Notebook com Windows e Python 3.10 ou superior; a instalação foi verificada com Python 3.12.
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
