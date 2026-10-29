# Direção automática de histórias — 0.21

O sistema prepara uma nova coleção original, **Pequenos segredos do 12**, com sete histórias completas. Cada vídeo apresenta seu conflito e entrega um desfecho próprio. A pessoa não precisa encontrar os capítulos anteriores para entender a trama. Lia, Eva e Davi continuam fictícios; suas experiências não são depoimentos sobre o produto divulgado.

## O que acontece sozinho

1. Ao preparar a coleção `standalone`, o sistema escolhe uma abertura entre alternativas escritas para aquela história e fixa o roteiro e a decisão na posição do calendário.
2. O produtor local monta um vídeo de cada vez com narração nova e cenas 3D originais verificadas. Alterna enquadramentos a cada até 3,25 segundos, mantendo o movimento da fonte durante os cortes e as trocas de legenda.
3. A voz gratuita do Windows entrega os instantes de início das palavras. As legendas usam esses tempos quando os eventos são válidos e completos. Caso contrário, a montagem usa estimativas e identifica isso nos metadados.
4. A revisão impede liberar uma montagem sem voz, com abertura acima de sete segundos, duração fora de 25–105 segundos ou legenda acima de 32 caracteres por segundo. Antes disso, verifica repetição de cenas, tamanho dos trechos e presença de um desfecho. Essas regras são limites locais de edição, não prova de qualidade artística ou de alcance.
5. A oferta continua em bloco comercial separado. O pacote verifica autorização, link, identificação de publicidade, hashes e revisão editorial correspondente ao roteiro. Não recria envios de capítulos já registrados no TikTok.

Os limites são hipóteses de produção. O TikTok descreve tempo assistido e outras interações como sinais de recomendação na sua [documentação do sistema de recomendações](https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content). Suas [orientações criativas para anúncios](https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en) destacam abertura, som, formato vertical e área segura. Aplicar essas orientações a ficção orgânica é uma escolha editorial; não garante distribuição ou vendas.

## Adaptação com resultados

O painel ainda recebe métricas por registro do titular. Não há sincronização automática de análises do TikTok nesta versão. Dados indisponíveis ficam desconhecidos, e observações acumuladas do mesmo vídeo não são somadas.

O diretor só considera vídeos diferentes com pelo menos 100 visualizações, tempo médio conhecido e observação feita pelo menos 24 horas após a publicação. Observações com mais de 14 dias são excluídas. São necessários pelo menos três vídeos elegíveis. Se a mediana da proporção assistida ficar abaixo de 40%, o próximo plano testa tomadas de até 2,5 segundos. Esses números são heurísticas locais, não critérios divulgados pelo algoritmo. A decisão muda apenas essa proposta de ritmo; não troca a abertura ao mesmo tempo, não acelera a voz, não escolhe um “melhor horário”, não atribui causalidade e não altera vídeos programados. Alternativas de abertura servem para corrigir uma opção que exceda o limite editorial de palavras.

Cada posição guarda a decisão escolhida. Uma métrica nova não muda um vídeo em produção nem invalida sua recuperação após reinício. Uma próxima preparação pode usar dados novos.

## Limites de autonomia

As sete histórias novas formam um catálogo finito, com roteiro previamente escrito; o aplicativo não inventa temporadas infinitas sozinho. A preparação usa o notebook ligado, sem serviço pago, e mantém a parada após falhas. Antes de uma montagem, exige pelo menos 256 MB livres. Após concluir, descarta somente cópias temporárias verificadas dos arquivos exportados e dos clipes, preservando os originais e projetos Blender. Uma parada pode ser retomada no painel depois de corrigir a causa; arquivos prontos não voltam à fila.

As cenas reaproveitam animações 3D de 540 × 960 a 12 quadros por segundo, exportadas em 720 × 1280 a 24 quadros com repetição. Os cortes não aumentam o detalhe ou a fluidez nativos. A boca não acompanha os fonemas da nova voz.

Preparação, revisão e pacote não são agendamento no TikTok. Os sete agendamentos da coleção anterior continuam protegidos pelos recibos locais. Para novos envios gratuitos, login e seleção de arquivo no TikTok Studio continuam dependendo do acesso disponível e das verificações do titular. O sistema não contorna bloqueios da ferramenta nem compra uma integração.

## Teste isolado

- Prepare `POST /api/stories/week/prepare` com `collection: "standalone"`, `start_date` futura ISO e `hour` inteiro, usando a sessão local. Devem existir sete posições globais 9–15, com planos fixados e nenhum envio externo.
- Registre observações de teste pequenas, recentes ou repetidas: não devem ativar ajuste. Três vídeos diferentes e maduros podem sugerir o experimento, sem declarar um vencedor.
- Interrompa uma montagem. Apenas uma versão completa, com o mesmo roteiro, decisão, produto e hash, pode ser recuperada.
- Remova a voz, alongue a abertura ou altere o roteiro depois da revisão: a produção ou o pacote precisa parar. Nunca marque o teste como postagem.
- Confira a reprodução inteira, a leitura das legendas, a continuidade do áudio e o enquadramento. A revisão automática não substitui a avaliação criativa de uma pessoa.
