# Validadores do projeto

O workflow **Validadores** executa em cada push e pull request e também pode ser iniciado pela aba Actions. Ele usa máquinas temporárias do GitHub; não usa seu notebook nem acessa suas contas de publicação.

| Verificação | O que confere |
| --- | --- |
| Testes Windows | Comportamento do aplicativo e proteções em Python 3.11, 3.12 e 3.13. |
| Fontes | Sintaxe de todos os arquivos Python e JSON rastreados. |
| JavaScript | Sintaxe de todos os arquivos JavaScript rastreados, usando Node.js 24. |
| Recursos do painel | Arquivos locais referenciados no HTML; rejeita scripts e eventos inline. |
| Privacidade | Rejeita arquivos locais e sensíveis no código e em todos os commits disponíveis. |
| Pacote | ZIP íntegro, sem links simbólicos ou dados privados, correspondente aos arquivos do commit. |
| Ruff | Erros de sintaxe, referências indefinidas e outros erros estáticos de Python selecionados. |
| Gitleaks | Padrões de credenciais no histórico completo; os valores são ocultados nos logs. |
| pip-audit | Vulnerabilidades conhecidas das dependências de execução, consultadas na base pública. |

As ações usam versões fixadas por commit. O Gitleaks usa uma versão e checksum explícitos. Dependabot propõe atualizações semanais de pacotes e ações, sem fazer merge automático.

Usamos runners padrão, sem cache ou upload de artefatos dos workflows. A execução em repositórios públicos com esses runners é gratuita conforme a [documentação do GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Validar no notebook

Use um clone Git atualizado do repositório, instale o aplicativo e execute **validar.bat**. Para essa validação de desenvolvimento, o Node.js LTS precisa estar disponível; ele não é necessário para usar o aplicativo. O comando equivalente é:

```powershell
.venv\Scripts\python.exe scripts\validate.py --report artifacts\validation-report.json
```

Essa execução confere fontes, recursos, privacidade dos caminhos, pacote e testes. Ela não abre o aplicativo nem usa os bancos de produção. O relatório contém nomes de verificações e erros técnicos. O histórico deve estar completo: uma cópia rasa é rejeitada. Para checar o histórico e o pacote é necessário usar uma cópia Git; o ZIP da release serve para usar o aplicativo, não para executar esses dois validadores de desenvolvimento.

A suíte inclui renderizações reais de MP4 e pode levar vários minutos em máquinas lentas. O validador permite até oito minutos para a suíte completa, preservando todos os testes. Se atingir esse prazo, reprova a etapa e mostra os últimos testes iniciados para ajudar a investigar; não considera a execução incompleta aprovada.

Ruff, Gitleaks e pip-audit são etapas adicionais de segurança no GitHub. `requirements-validation.txt` contém ferramentas de desenvolvimento e não altera as duas dependências do aplicativo. Para reproduzir Ruff e pip-audit localmente, instale essas ferramentas em um ambiente separado.

## Quando falhar

Abra **Actions → Validadores → execução → etapa que falhou**. Corrija o problema e envie uma nova alteração. Falhas de conexão de uma auditoria não são consideradas aprovação de segurança. Não desative a verificação ou ignore um alerta apenas para obter um resultado verde.

Se houver uma credencial real no histórico, revogue-a e substitua-a no provedor antes de tratar o histórico. Apagar somente o arquivo atual não remove o segredo dos commits anteriores. Nunca copie a credencial para uma Issue ou log.

Esses validadores detectam classes específicas de problemas e não garantem ausência de todas as falhas. Não validam sua afiliação, atribuição de comissão, conversão comercial nem o primeiro envio real a uma rede social. As integrações externas continuam usando respostas simuladas nos testes.
