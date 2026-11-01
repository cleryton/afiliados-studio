# Envio sem selecionar cada arquivo

O navegador precisa receber autorização para ler os MP4s do projeto. Essa configuração é independente de estar logado no TikTok ou de ter o Metricool conectado.

## O reparador

Execute **reparar_acesso_videos.bat** na pasta do projeto. Ele usa a opção oficial `--workspace` do Chrome DevTools para incluir somente **data/stories**, com o caminho absoluto desta instalação. Mantém a versão fixa do conector e as demais configurações. Não habilita acesso irrestrito, não copia vídeos para outra pasta e não abre um túnel.

Antes de alterar, grava uma cópia local de recuperação junto da configuração da integração. Nunca envia essa configuração ao GitHub. Repetir o reparador não acrescenta a mesma autorização outra vez.

O reparador altera o `.mcp.json` da instalação ECC no cache local. Uma atualização desse plugin pode substituir a configuração; nesse caso, execute o reparador novamente. Ele não altera o código da integração nem a verificação de caminhos. Na linha de comando, `--config` permite escolher a configuração exata; sem esse argumento, usa a versão numérica mais recente encontrada no cache ECC.

## Depois de reparar

1. Salve seu trabalho e feche e abra o Codex, para recarregar a integração.
2. Retome esta conversa. Se a sessão do TikTok tiver encerrado, entre pessoalmente no perfil exclusivo do projeto.
3. O próximo teste deve usar o comando normal de envio do navegador, com o MP4 no caminho original. O teste precisa ser aceito antes de considerar o acesso resolvido.
4. Confira perfil, capítulo, legenda, identificação comercial, IA, data e horário antes de confirmar cada agendamento. Um pedido aceito precisa aparecer novamente na lista após recarregar a página.

Salvar a configuração não comprova que o processo em execução já a carregou. O reparador não publica nada e não torna o aplicativo um publicador contínuo. A criação local, a sessão do navegador e a rotina de publicação são partes distintas. O Metricool conectado à conversa também não dá acesso automático aos arquivos do notebook.

Se o envio continuar recusado após recarregar a integração, preserve a mensagem do erro e confira qual configuração foi carregada. Não mova os arquivos para pastas temporárias, não desative a verificação de caminhos e não habilite acesso irrestrito como solução.

Fonte: [opções oficiais do Chrome DevTools, `--filesystemRoot` / `--workspace`](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/configuration.md).
