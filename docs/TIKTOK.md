# TikTok: conta, conteúdo e publicação

## Histórias de ficção — versão 0.14

Abra **Histórias no TikTok** no painel. **Preparar os três episódios** coloca a minissérie original **A chave do 12** na fila local. Os episódios são gerados em ordem, com imagens realistas de personagens fictícios, movimento de câmera, narração pt-BR do Windows e legendas aproximadas por trechos. O terceiro encerra a história.

Para divulgar um produto, selecione um cadastro ativo e autorizado em **Usar a história para divulgar um produto** e confirme as características. **Adicionar oferta e remontar episódios** acrescenta publicidade ao final, em cartões neutros, preservando a ficção. Os personagens não são apresentados como clientes ou depoimentos. A legenda preserva o link de afiliado e identifica a comissão possível. O aplicativo não inventa descontos, resultados ou provas de uso. Reaplicar a mesma oferta é idempotente; alterações no produto ou retirada da autorização exigem revisão e nova montagem antes de usar as prévias.

O campo **@ do perfil exclusivo** registra o destino pretendido. Não contém senha e não autentica o TikTok: uma sessão aberta no navegador e uma integração de publicação são estados diferentes. Confira o @ no próprio TikTok antes de enviar um vídeo. A versão atual não publica automaticamente esses episódios. Uma publicação realizada pelo navegador precisa ter resultado conferido na plataforma.

Em vídeos com oferta, ative tanto a indicação nativa de IA quanto a identificação comercial para promoção de terceiros. Consulte o [guia oficial no navegador](https://ads.tiktok.com/resources/help/article/how-to-turn-on-the-commercial-content-disclosure-setting-in-tiktok?lang=en-GB). A legenda não substitui esses controles. Não anuncie link na bio se ele não existir ou não estiver habilitado: o TikTok pode exigir seguidores ou registro empresarial para links clicáveis. O sistema mantém o endereço na descrição e orienta copiar e abrir se não houver link clicável.

As três imagens do piloto acompanham `assets/story-pilot`, com referências e prompts no README da pasta. Foram geradas durante a preparação do projeto, com referência da protagonista para manter sua aparência; não existe geração ilimitada de novas imagens ou novas histórias em segundo plano. A versão 0.15 monta planos curtos, objetos animados separadamente e efeitos locais; os personagens ainda não têm animação corporal ou sincronização labial. Para usar clipes em movimento por cena ou remontar episódios antigos, veja [Cenas em movimento](CENAS_EM_MOVIMENTO.md).

Assista a cada episódio, confira o texto, a voz e as legendas e baixe o MP4, o SRT e a legenda do post. Ausência de voz pt-BR aparece como aviso; erro na montagem oferece uma nova tentativa local, sem duplicar a temporada. Reiniciar o aplicativo retoma episódios interrompidos. Essa fila não envia episódios para YouTube ou Buffer, mesmo que essas contas estejam configuradas.

Crie um perfil exclusivo para o projeto no TikTok, conclua pessoalmente dados verdadeiros, termos e verificações e confira o @ antes de publicar. Conta ainda não criada ou login em outra janela não são uma conexão do aplicativo. A versão 0.14 continua sem integração de postagem pública automática no TikTok. Não forneça senha ou código ao estúdio.

Ao publicar as imagens realistas e a voz sintética deste piloto, ative a indicação nativa de conteúdo gerado por IA e preserve a descrição de ficção. Consulte a [orientação oficial sobre IA](https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content). Aprovação de conta, visualizações e monetização não foram verificadas por preparar vídeos locais.

Conferido em 23 de outubro de 2026. Você precisará de uma conta sua para usar o TikTok como canal. Pode criá-la pelo aplicativo ou pelo [site oficial](https://www.tiktok.com/). Essa conta ainda não libera a publicação automática do Afiliados Studio.

## O que funciona nesta versão

- Gerar MP4 vertical com roteiro, imagem autorizada opcional, narração local, texto e legenda do post.
- Baixar os arquivos e concluir a publicação no TikTok.
- Opcionalmente, encaminhar rascunhos pelo Buffer já implementado; eles não são tratados como publicações confirmadas.

Antes de publicar um vídeo de afiliado, confira o produto, seu link e os materiais. Ative a identificação comercial nativa indicada pelo TikTok para promoção de terceiros; escrever “Publicidade” na legenda não substitui esse controle. O [guia oficial de identificação comercial](https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/promoting-a-brand-product-or-service) explica a configuração no aplicativo e no navegador.

## Por que ainda não publica sozinho

A [documentação oficial da API direta](https://developers.tiktok.com/docs/en/content-sharing-guidelines) restringe clientes sem auditoria a publicação privada e declara que uma ferramenta para contas próprias ou da equipe não é um uso aceito. Também exige uma experiência de publicação com escolhas e consentimento do criador. Criar uma conta pessoal ou uma conta de desenvolvedor não elimina esses requisitos.

O [Buffer oferece API inclusive no plano Free](https://buffer.com/api). Entretanto, na [referência consultada](https://developers.buffer.com/reference), o input de metadados de TikTok documenta indicação de conteúdo gerado por IA e título; não confirmei um controle de identificação comercial que permita fechar o fluxo automático de afiliados. Essa é a razão para manter o envio atual como rascunho, sem prometer postagem pública automática.

Não é necessário contratar serviços pagos nem criar um aplicativo de desenvolvedor para testar a geração local. O primeiro teste de conta e publicação deve acontecer depois de existir uma integração compatível confirmada, ou pela conclusão manual no próprio TikTok. Não há promessa de aprovação da integração, alcance ou vendas.
