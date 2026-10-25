# Conteúdo e resultados do TikTok

Em **Histórias no TikTok → Melhorar o próximo capítulo**, o estúdio prepara roteiros curtos dos capítulos 2 e 3 de *A chave do 12*. São hipóteses editoriais para experimentar: conflito na primeira frase, progressão sem recapitulação longa, revelação e continuidade. A pergunta da legenda trata do conflito dos personagens, sem pedir comentários repetidos ou prometer prêmios.

A orientação de estrutura — abertura, desenvolvimento e encerramento — e de edição com movimento vem dos [Creative Codes do TikTok](https://ads.tiktok.com/business/en-US/creative-codes). A fonte trata de criação publicitária; aplicar esses princípios à minissérie é uma escolha editorial do projeto, sem comprovação de aumento de alcance orgânico nesta conta.

## Criar o próximo capítulo em 3D

Com o Blender local instalado e a oferta já autorizada, execute na pasta do projeto:

```powershell
.venv/Scripts/python.exe animation3d.py --episode 2 --with-current-offer
```

Use `--episode 3` para o desfecho. O padrão continua sendo o primeiro capítulo, preservando o comando anterior. A opção de reaproveitar o piloto aplica-se somente ao capítulo 1. Os capítulos 2 e 3 usam seis cenas curtas originais, os mesmos atores e um único bloco comercial final mais breve. A identificação de publicidade permanece na imagem, na narração e na legenda; as características verificadas e o link próprio ficam na legenda. Não são depoimentos dos atores.

Quando a montagem e a decodificação terminam, a prévia mostra o número correto do capítulo. Roteiros sugeridos no painel não significam vídeos já renderizados. A prévia anterior e os arquivos de capítulos anteriores são preservados durante uma geração. A criação local não posta nem altera um vídeo agendado no TikTok Studio.

## Registrar desempenho real

Abra a [análise do TikTok Studio](https://www.tiktok.com/tiktokstudio/analytics), escolha o vídeo e use **Registrar números do TikTok Studio** no painel local. A coleta ainda é manual. Não há login, leitura em segundo plano nem sincronização de métricas desta conta pelo aplicativo.

1. Cole o link completo do vídeo publicado, com o mesmo @ indicado no projeto.
2. Informe a data real da publicação no horário do computador e a duração do MP4 em segundos. Vídeo ainda agendado não é uma publicação realizada.
3. Digite as contagens acumuladas e os dados de retenção exibidos para esse vídeo. **Em branco significa indisponível; 0 significa zero observado.** O campo de novos seguidores refere-se ao vídeo, não ao total do perfil.
4. Salve novamente em torno de 24 h e 72 h da publicação. Cada observação é guardada, e o painel mostra a mais recente de cada vídeo, sem somar contagens acumuladas.

Interações por visualização = (curtidas + comentários + compartilhamentos) ÷ visualizações × 100. O cálculo exige as três contagens e visualizações maiores que zero. Tempo médio dividido pela duração pode superar 100% por repetição e não equivale à porcentagem de espectadores que chegaram ao fim; conclusão só aparece quando esse dado foi informado. Não há estimativa de vendas ou renda a partir das visualizações.

## Experimento inicial

Teste um capítulo novo por dia, em ordem, usando o primeiro horário como hipótese. Não há evidência nesta conta para chamar um horário de melhor. Compare retenção e conclusão entre capítulos antes de mudar abertura, duração ou bloco comercial. Comparações entre histórias diferentes não isolam uma causa: público, distribuição e assunto também mudam.

As próximas hipóteses podem responder aos resultados observados: se a curva mostrar abandono na abertura, tornar o conflito mais claro; se a queda coincidir com a oferta, testar um bloco menor; se espectadores voltarem para a continuação, manter personagens e continuidade. Essas decisões exigem dados reais e não alteram automaticamente um vídeo remoto. A minissérie termina no capítulo 3; não existe geração infinita de temporadas.

## Conferência do tester

- Conta sem registros: nenhum resultado fictício; sem melhor horário ou abertura vencedora.
- Registro com 0 visualizações e retenção vazia: 0 visualizações, retenção indisponível e taxa de interação indisponível.
- Nova observação do mesmo vídeo: apenas a última contagem no cartão, mantendo as duas observações no banco local.
- Link de outro perfil, contagem negativa, porcentagem acima de 100 ou publicação futura: recusar sem gravar.
- Formulário parcialmente preenchido: a atualização de andamento não apaga o conteúdo ao tirar o foco.
- Geração do capítulo 2: seis cenas, voz, legendas, identificação de publicidade, link preservado, prévia com número 2 e MP4 decodificável.
- Publicação: confirmar no TikTok Studio. Um roteiro pronto, uma prévia local e uma programação futura têm estados diferentes.

Dados ficam no SQLite dentro de `data/`, fora do GitHub. Nenhuma contratação ou impulsionamento pago faz parte dessa função.
