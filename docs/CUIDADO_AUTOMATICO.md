# Cuidado automático das histórias — 0.22

Esta rotina funciona no notebook, sem serviços pagos. Ela cuida das coleções já preparadas; não cria um catálogo infinito, não faz login em redes e não envia publicações. O YouTube pessoal e a integração paga continuam independentes e desativados nesta operação.

## Criação sem acompanhamento

- **Falta de espaço:** aguarda pelo menos 256 MB livres, conferindo novamente depois de cinco minutos. Uma espera anterior à montagem não consome tentativa nem inicia processos repetidos.
- **Interrupção temporária:** um tempo limite ou uma falha reconhecida de falta temporária de recursos permite até três tentativas reais. As esperas são de um e cinco minutos. O estado persiste após reiniciar o aplicativo.
- **Montagem interrompida:** procura o arquivo completo correspondente ao mesmo roteiro, decisão editorial, produto e posição do calendário. Se existir e passar na conferência, aproveita esse arquivo. Uma terceira interrupção sem arquivo válido exige revisão.
- **Falha de qualidade, arquivo alterado, perfil ou produto incorreto:** para para revisão. O programa não tenta resolver uma permissão ou mudar uma oferta sozinho.

As esperas preservam a ordem dos episódios. Um capítulo posterior não passa à frente de um capítulo aguardando recursos. Ao terminar a coleção, a criação fica ociosa.

## Arquivos e pacotes

O cuidado local verifica a coleção mais recente ao iniciar e a cada quinze minutos, quando o produtor estiver livre. Confere o vídeo, os arquivos de apoio, a oferta, o destino e o pacote. Se apenas o ZIP estiver ausente ou corrompido, refaz o pacote a partir dos arquivos válidos. Não remonta o vídeo e não muda sua legenda.

Após três reparos de pacote malsucedidos, a rotina espera uma ação explícita em **Conferir agora e reparar pacotes**. Falta de espaço apenas adia a conferência. Um arquivo essencial ausente ou alterado exige revisão; não é substituído silenciosamente.

A limpeza automática se limita às cópias temporárias de montagens completas dentro de `data/story-week/renders`. Antes de apagar um arquivo, confere o caminho e a igualdade com uma cópia principal preservada. Clipes de trabalho só são removidos quando o original correspondente ainda existe no banco de cenas. Não apaga vídeos principais, projetos Blender, publicações, pastas inteiras ou arquivos personalizados.

## Pausa e próxima publicação

**Pausar cuidado e próximas montagens** persiste após reiniciar. A rotina não desfaz essa escolha. Uma montagem já iniciada pode concluir seu arquivo local. A pausa não altera agendamentos salvos no TikTok.

O painel apresenta o primeiro capítulo sem registro nativo, em ordem, com prévia, legenda e pacote quando disponível. Datas são propostas locais. Um horário passado recebe um aviso; nunca é promovido a publicação confirmada.

## Publicação externa

Nesta versão, novos envios gratuitos continuam dependendo do login e da seleção dos arquivos no TikTok Studio. A rotina não contorna restrições de acesso da ferramenta de navegador e não contrata planos. A documentação do [Upload-Post](https://docs.upload-post.com/guides/post-to-tiktok-api/) informa que TikTok exige plano pago. A referência consultada do [Buffer](https://developers.buffer.com/types/TikTokPostMetadataInput.html) mostra identificação de IA, mas não confirma o campo de identificação comercial necessário a estas ofertas; por isso não foi apresentada como solução completa.

## Teste isolado

1. Simule disco cheio antes de gerar: estado de espera, zero novas tentativas e nenhum novo produtor até a próxima conferência elegível.
2. Simule três tempos limites: esperas persistentes e parada após a terceira tentativa. Nenhuma publicação externa deve ser criada.
3. Pause durante uma espera e reinicie: a pausa deve continuar até retomada explícita.
4. Corrompa somente um ZIP de teste: deve ser reparado com o MP4 original intacto. Altere o MP4: deve pedir revisão, sem recriá-lo.
5. Simule três falhas de reparo: não deve continuar tentando até a conferência explícita.
6. Coloque uma cópia idêntica de trabalho e um arquivo personalizado no diretório do teste. Somente a cópia validada pode ser retirada.
7. Mude o perfil ou revogue o produto: a rotina deve reter a operação e os links do próximo envio.
