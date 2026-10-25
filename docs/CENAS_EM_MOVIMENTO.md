# Montagem de episódios com movimento

A montagem local alterna planos gerais, detalhes e reações em tomadas de até quatro segundos. A chave gira, cartas saem do envelope, a fotografia desliza e a porta tem uma abertura composta em camadas. Esses objetos se movem independentemente do fundo. A montagem acrescenta ambiente discreto e sons originais de metal, papel e batidas, sintetizados no notebook; não baixa músicas de terceiros.

São composições a partir de imagens preparadas e objetos com transparência, não um modelo de geração de vídeo. Os personagens continuam sem atuação corporal e sem sincronização da boca. Para ter essas ações, forneça clipes próprios ou licenciados. Não há serviço pago, chave de IA ou geração ilimitada de clipes configurada.

## Usar e conferir

Em **Histórias no TikTok**, use **Remontar com cortes e movimento** em um episódio pronto. Isso coloca somente esse episódio na fila local, oculta sua prévia enquanto trabalha e não modifica publicações já feitas no TikTok. Não cria outro episódio nem repete um envio. Em erro, o MP4 anterior é preservado em disco e a tela oferece tentar novamente.

Assista ao resultado: os cortes devem acontecer independentemente das legendas; o movimento de fundo não deve reiniciar a cada frase. A legenda deve continuar legível e os efeitos não devem encobrir a voz. O SRT usa temporização aproximada por texto. O bloco comercial continua separado da ficção, sem depoimentos dos personagens. Publicação permanece um passo externo.

Os arquivos novos registram `editing_style`, `shot_timeline`, `character_animation` e `sound_design` em `roteiro.json`, junto da duração medida e do hash do MP4. Uma versão antiga só recebe a nova montagem ao ser remontada; não considere todos os arquivos existentes atualizados apenas por atualizar o programa.

## Clipes reais por cena (configuração avançada local)

Guarde os arquivos em `data/story-clips/`, com nomes fixos `episode-2-scene-1.mp4`, por exemplo. O número da cena corresponde à ordem do roteiro de ficção, começando em 1; não inclui publicidade. Cada arquivo deve ter até 200 MB e a cena precisa ter origem e autorização registradas. Não use links remotos ou caminhos de outras pastas.

Crie `data/story-clips/manifest.json` com este formato ilustrativo:

```json
{
  "2:1": {
    "file": "episode-2-scene-1.mp4",
    "approved": true,
    "source": "Gravação própria; participantes autorizaram o uso",
    "sha256": "SUBSTITUA_PELO_HASH_SHA256_DO_ARQUIVO"
  }
}
```

Obtenha o hash no PowerShell com `Get-FileHash -LiteralPath 'data/story-clips/episode-2-scene-1.mp4' -Algorithm SHA256`; copie o hash em letras minúsculas. Revise origem e direitos de uso antes de marcar `approved: true`. Isso registra sua autorização local, não verifica uma licença em nome de terceiros. Os vídeos e esse manifesto ficam somente no notebook e fora do GitHub.

Remonte o episódio depois de salvar. A cena usa o clipe em movimento, com enquadramento vertical central, 24 quadros por segundo e legendas existentes. Um clipe curto repete até terminar a narração; o áudio original é removido para manter a voz da história e os efeitos locais. Não há detecção automática de rosto ou continuidade de atuação. Prepare clipes verticais com os personagens e a ação certos.

Sem entrada para uma cena, o aplicativo usa a composição local. Se houver uma entrada incompleta, arquivo alterado ou vídeo inválido, a montagem falha e preserva o MP4 anterior. A origem e o hash dos clipes usados ficam no roteiro exportado. Uma mudança no manifesto exige remontar; versões já exportadas não são retiradas de publicações externas.
