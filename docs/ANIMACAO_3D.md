# Piloto em animação 3D

O projeto inclui um piloto curto de **A chave do 12**, com Lia, Eva e Davi modelados em 3D, um apartamento, móveis, iluminação, chave, carta, fotografia e uma porta articulada. Os modelos são originais e construídos pelo código local; não há avatares baixados nem um serviço de geração de vídeo conectado.

O estilo é de bonecos 3D. Ombros, cotovelos, cabeça e olhos têm movimentos próprios. A abertura da boca é procedural e aproximada, sem sincronização por fonema; os personagens ficam apoiados no chão, sem um sistema de caminhada ou captura de movimento. A narração é sintética em português. A única imagem de IA usada dentro do cenário é a fotografia fictícia mostrada por Eva.

## Assistir

Após uma geração concluída, **Histórias no TikTok** exibe **Novo · Animação 3D**, com reprodução e download. Essa prévia mostra o último capítulo 3D concluído. Sem a opção de capítulo, a geração continua usando a adaptação do episódio inicial. Os episódios já existentes e as publicações do TikTok continuam com suas versões; criar uma prévia não publica nem substitui um vídeo remoto.

Quando solicitada com oferta, a publicidade usa o produto ativo e autorizado, em um bloco final separado dos personagens. O link fica na descrição. O produto e seus dados são novamente conferidos antes de disponibilizar a prévia. Não há resultados de venda presumidos.

## Gerar no notebook

O Blender é uma dependência opcional para esta produção. Baixe-o no [site oficial](https://www.blender.org/download/), usando o pacote portátil para Windows se preferir. A geração não exige uma conta de serviço de IA. O código foi preparado para o Blender 4.5 LTS; registre a versão utilizada e confira o resultado ao trocar de versão.

Exemplo no PowerShell, na pasta do projeto:

```powershell
.venv/Scripts/python.exe animation3d.py --blender 'C:/caminho/Blender/blender.exe' --with-current-offer
```

Sem `--with-current-offer`, o piloto é apenas ficção. A opção comercial exige uma oferta previamente ativa e autorizada no estúdio. O processo gera os seis trechos 3D, monta voz, legendas e publicidade, decodifica o MP4 e só então disponibiliza a nova prévia. Fechar o processo antes do fim não deve substituir a prévia pronta anterior. Não há retomada automática dos quadros de uma produção 3D interrompida.

O padrão renderiza em 540 × 960, com 12 quadros de animação por segundo, e exporta MP4 em 720 × 1280, a 24 quadros por segundo, repetindo quadros. A ampliação não acrescenta detalhes. É uma escolha para notebook com vídeo integrado. Para mais definição e fluidez, use `--width 720 --height 1280 --fps 24`; isso aumenta o trabalho de renderização. `--samples 12` é o padrão; valores maiores reduzem ruído e demoram mais.

## Arquivos e edição

- `data/story-3d/<id>/scene-1/scene.blend` e os demais trechos guardam os projetos nativos com materiais, fotografia incorporada e animação gravada nos controles. Podem ser abertos no Blender sem habilitar execução automática de scripts.
- Cada trecho tem `motion-state.json`, com câmera, orientação, poses, movimentos dos braços e contato dos pés em quadros amostrados.
- Os quadros PNG intermediários são removidos somente depois da montagem de cada clipe. Clipes e projetos nativos permanecem no notebook.
- O MP4 final, a legenda, o SRT e `roteiro.json` ficam em `data/stories/<id>/`. O roteiro registra o tipo 3D, resolução original, taxa de animação e limitações da boca.
- `data/story-3d/preview.json` aponta apenas para a última prévia completa. Arquivos locais e registros de renderização ficam fora do GitHub.

A fila comum de três episódios ainda usa a montagem anterior. O piloto 3D é gerado por esse comando próprio e exibido separadamente no painel; não há geração contínua de temporadas 3D nem postagem automática incorporada a ele.


## Melhoria da revelação — versão 0.17

A cena final pode usar a intensidade medida no áudio para abrir a boca e mover a expressão de Eva durante sua fala. Continua sem reconhecimento de palavras ou sincronização por fonema. Para reaproveitar cinco clipes anteriores com hash, roteiro, resolução e taxa conferidos, use `--reuse-pilot ID_DO_PILOTO_ANTERIOR` junto das opções normais. Essa opção remonta a oferta e a cena final, preservando a prévia anterior até terminar. Reaproveitar cenas não gera um novo capítulo para publicação.

## Continuação curta — versão 0.18

`--episode 2` e `--episode 3` criam os próximos capítulos originais com os mesmos atores. Usam conflito na primeira frase e publicidade final resumida. `--reuse-pilot` continua restrito ao capítulo 1. A última prévia passa a mostrar o capítulo gerado; arquivos anteriores permanecem no notebook. Veja [Conteúdo e resultados](ENGAJAMENTO_TIKTOK.md).
