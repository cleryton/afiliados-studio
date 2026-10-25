# Biblioteca e operação

**Histórias no TikTok** mostra os capítulos 3D concluídos em ordem, com prévia, MP4 e legenda. A biblioteca guarda a versão mais recente de cada capítulo. A minissérie atual tem três capítulos; não há produção infinita de histórias.

Cada cartão distingue:

- **Arquivo local · aguardando envio:** o vídeo foi produzido no notebook, mas não há recibo de envio ao TikTok.
- **Agendamento registrado no TikTok:** existe uma conferência salva da programação nativa.
- **Horário agendado atingido; conferir no TikTok:** o registro continua sendo de agendamento; a passagem do tempo não comprova publicação.
- **Publicação registrada no TikTok:** existe um registro de conferência da publicação. A interface usa a última observação salva, sem sincronização contínua.

Os registros locais usam `agendamento-tiktok.json` ou `publicacao-tiktok.json` na pasta do vídeo. Não devem ser inventados para liberar a fila. Um capítulo 3D com agendamento ou publicação registrados para o mesmo perfil é retido se houver uma tentativa posterior de enfileirá-lo pela integração opcional, evitando duplicação entre os dois caminhos.

## Limpar versões substituídas

**Limpar vídeos locais substituídos** apaga somente MP4s antigos da biblioteca. Uma versão 2D só é retirada depois que o mesmo capítulo tem uma versão 3D concluída e com hash válido. A operação conserva:

- a versão 3D atual de cada capítulo;
- qualquer vídeo com arquivo de recibo, mesmo se esse recibo estiver danificado;
- vídeos referenciados na fila de publicação ou em geração;
- projetos nativos do Blender, roteiros, legendas e registros.

Os caminhos precisam permanecer dentro da pasta local de dados. Alterações inesperadas nos hashes interrompem a limpeza. Versões retiradas ficam com estado arquivado e não são reativadas ao aplicar outra oferta. Um segundo clique não deve excluir novamente os mesmos arquivos. A ação não apaga posts ou agendamentos do TikTok.

## Envio sem tocar no computador

A integração opcional pode publicar e confirmar pedidos quando estiver conectada a um provedor que permita TikTok e as marcações comerciais/IA. Na conta gratuita observada, esse acesso permanece bloqueado pelo provedor; o aplicativo não contrata planos.

O agendamento nativo do TikTok Studio dispensa manter o notebook ligado após o arquivo ter sido enviado e a programação confirmada. Até essa confirmação, o arquivo local não está agendado. Usar o navegador para enviar arquivos também depende de sessão válida, acesso permitido à pasta de origem e eventuais verificações feitas pelo titular. Se a ferramenta negar acesso à pasta, esse impedimento precisa ser resolvido na configuração da integração; não existe um envio automático confirmado enquanto a restrição persistir.

## Teste

1. Confira que todos os capítulos concluídos aparecem, e que arquivos em geração ainda não aparecem como prontos.
2. Use registros de teste claramente identificados, somente em `data-tester`, para verificar estados de programação futura e passada. Nenhum deles deve se transformar sozinho em publicado.
3. Prepare uma cópia antiga sem recibo e uma substituta 3D válida. A limpeza deve retirar apenas a antiga e atualizar sua disponibilidade no painel.
4. Repita com recibo danificado, referência na fila e substituto alterado. Em todos esses casos, o arquivo protegido deve permanecer.
5. Confira os downloads no computador e no celular, sem conteúdo saindo da largura da tela. O modo tester continua bloqueando conexões e envios externos.
