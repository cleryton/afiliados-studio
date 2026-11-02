# Cenas curtas com ações em 3D

O estúdio pode produzir três demonstrações originais de seis segundos, com os personagens Lia e Eva: chegada ao apartamento, entrega da chave e revelação do desenho. São animações de objetos e personagens modelados no Blender, com articulações, passos e gestos; não dependem de um serviço pago. Os clipes são verticais, em 540 × 960, a 18 quadros por segundo, sem narração ou música.

No painel **Histórias no TikTok → Cenas animadas para assistir**, cada demonstração concluída tem um player e um botão de download. Elas ficam separadas dos capítulos e da agenda de postagem. Criar esses clipes não agenda uma publicação.

Para gerar as três cenas novamente, com Blender já instalado:

```powershell
.venv/Scripts/python.exe animation_demos.py render
```

A geração é explícita e local. Não é executada a cada abertura do painel. Pode demorar vários minutos, conforme o notebook. Os projetos editáveis, quadros e medições ficam em `data/animation-demos/<produção>/`; os MP4s e capas usam a biblioteca de mídia local. O catálogo só é substituído quando os três vídeos terminaram de renderizar e decodificaram sem erro. Uma falha preserva o catálogo anterior.

Os modelos mantêm suas proporções originais. O movimento usa articulações de dois segmentos nos braços e pernas, apoio dos pés durante cada passo, controle de contato com a chave e o papel, piscadas e movimento discreto de câmera. Cada produção mede todos os quadros e grava um resumo e amostras do estado do Blender em `motion-state.json`, antes da exportação. Erros acima de 5 mm no alcance das mãos ou 15 mm no apoio e deslocamento por quadro dos pés interrompem a renderização.

As verificações geométricas não substituem a revisão visual: confira o enquadramento, possíveis objetos à frente dos rostos, os gestos e a fluidez ao assistir. A boca permanece em expressão de repouso; esses clipes não oferecem sincronização de fala. Para um episódio narrado, ainda é necessário preparar o roteiro, voz, montagem e revisão comercial correspondentes.
