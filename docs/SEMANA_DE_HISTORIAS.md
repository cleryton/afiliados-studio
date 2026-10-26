# Semana de histórias e entrega local

O calendário de **Histórias no TikTok** prepara sete datas consecutivas, no fuso de São Paulo. O primeiro plano desta operação é de **26/10 a 01/11/2026, às 18h**, com os capítulos globais 2 a 8. Esse horário é uma proposta inicial, não um melhor horário comprovado por métricas.

Os dois primeiros vídeos concluem *A chave do 12*. Os cinco seguintes formam o novo arco original *O último desenho*, com Lia, Eva e Davi. A narrativa tem conclusão e os personagens continuam sendo fictícios. A oferta autorizada aparece num bloco comercial final separado da história.

## Estados

- **Na fila de criação:** o roteiro está previsto, mas ainda não há MP4 completo.
- **Gerando vídeo local:** o processo está produzindo o capítulo no notebook.
- **Arquivo pronto · envio pendente:** a montagem foi concluída; o arquivo não foi enviado ou agendado por esse estado.
- **Preparação interrompida:** houve erro ou alteração do destino/produto. A rotina para para evitar repetições sem fim.
- Registros de postagem do TikTok, quando existentes, continuam sendo mostrados separadamente. A data proposta nunca é promovida automaticamente a publicação.

## Produção

O programa principal verifica a existência de trabalho local pendente. Um processo separado produz os capítulos em série, com trava no sistema operacional para impedir dois produtores simultâneos. Isso evita alterar a pasta de dados usada pelo servidor durante a montagem. Depois de um reinício, uma montagem já concluída e correspondente ao roteiro/produto pode ser adotada e empacotada; arquivos incompletos não são apresentados como prontos.

Os capítulos novos usam cenas 3D originais já produzidas no Blender, com gestos e câmeras reais, repetidas ou encurtadas conforme a nova narração. O desenho de papel é um novo objeto 3D feito de geometria. Não há geração de avatares ou vídeo por serviço pago. A narração e as legendas são novas em cada capítulo. A reutilização dos gestos significa que a boca não acompanha as palavras do novo áudio; isso fica registrado no roteiro exportado.

O notebook precisa estar ligado para produzir esses arquivos. A preparação não publica em nenhuma rede, não altera o YouTube pessoal e não contrata serviços. O acesso à pasta pela ferramenta de navegador continua sendo um requisito separado para os próximos envios.

Para criar um plano local por API, envie `start_date` em formato ISO e `hour` inteiro para `POST /api/stories/week/prepare`, com o token local da sessão. A ação exige uma oferta ativa e autorizada e o perfil exclusivo definido. Repetir perfil/data retorna o plano existente. O catálogo atual é finito; uma nova semana não deve repostar capítulos já registrados no TikTok.

## Pacote completo

Cada capítulo sem recibo pode ter um ZIP com:

- `video.mp4`: montagem final;
- `capa.png`: quadro original do próprio vídeo, sem gerar outra imagem;
- `legenda.txt` e `legendas.srt`;
- `publicacao.json`: perfil, hashes e marcações necessárias de IA/publicidade, com `scheduled: false`;
- `LEIA.txt`: instruções e estado local.

O manifesto não é um recibo do TikTok. Preparar ou baixar o ZIP não envia o vídeo. Ao preparar e ao baixar, o sistema verifica os arquivos, o destino, a oferta, o link e a identificação comercial. Uma mudança na legenda, no MP4, no perfil ou na autorização pode invalidar o pacote. Uma cópia corrompida do ZIP é recusada. Capítulos com registro nativo ou pedido existente na fila de publicação não geram outro pacote de envio.

## Teste do usuário tester

1. Em dados de teste, crie um plano de sete dias e repita a mesma solicitação: deve haver apenas sete posições.
2. Confira fuso e mudança de mês. Datas são planejamento local, mesmo depois de passarem.
3. Interrompa uma preparação de teste. Uma montagem completa deve ser adotada; uma incompleta volta à criação sem se tornar publicação.
4. Troque o perfil ou a autorização do produto: produção e pacotes devem ser retidos.
5. Altere um arquivo depois de empacotar: o download precisa ser recusado até novo preparo válido.
6. Confira o conteúdo do ZIP, a reprodução local, as capas e as legendas. Nada desse teste deve criar postagem externa.
