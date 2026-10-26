"""Finite original sequel; global episode numbers preserve posting order."""
NUMBERS=tuple(range(1,9))
WEEK_NUMBERS=tuple(range(2,9))
STORIES={
4:{'title':'O desenho com uma porta a mais','question':'Você procuraria a porta que não aparece no corredor?','scenes':[
 {'visual':'drawing','text':'O desenho mostrava o apartamento doze. Mas havia uma porta a mais.'},
 {'visual':'room','text':'Eva reconheceu o papel. A mãe desenhava ali quando era jovem.'},
 {'visual':'building','text':'Davi viu a porta desenhada e ficou em silêncio.'},
 {'visual':'door','text':'No corredor, Lia encontrou a marca de uma parede refeita.'},
 {'visual':'key','text':'Atrás do rodapé, uma chave estava presa com fita.'},
 {'visual':'drawing','text':'No verso do desenho, uma frase: devolva o que é dele. Mas de quem?'}]},
5:{'title':'O nome escrito na caixa','question':'Por que alguém guardaria uma caixa sem tentar devolvê-la?','scenes':[
 {'visual':'key','text':'A chave escondida tinha um número. Davi reconheceu o antigo armário do depósito.'},
 {'visual':'building','text':'Ele trouxe uma caixa. O nome escrito nela não era o da mãe: Miguel.'},
 {'visual':'room','text':'Miguel era um vizinho, contou Eva. Saiu do prédio antes de eu nascer.'},
 {'visual':'drawing','text':'Dentro, havia desenhos de uma menina e uma carta nunca entregue.'},
 {'visual':'room','text':'Davi pediu que fechassem a caixa. Lia perguntou por quê.'},
 {'visual':'door','text':'Porque fui eu que mandei Miguel embora, ele respondeu. E eu estava errado.'}]},
6:{'title':'A acusação que ninguém corrigiu','question':'Um pedido de desculpas basta depois de tantos anos?','scenes':[
 {'visual':'building','text':'Davi expulsou um inocente do prédio. Agora precisava explicar por quê.'},
 {'visual':'room','text':'Um dinheiro desapareceu. Miguel consertava os móveis. Foi fácil acusar quem estava de passagem.'},
 {'visual':'drawing','text':'A mãe de Lia encontrara o dinheiro dias depois, atrás de uma gaveta.'},
 {'visual':'room','text':'Ela tentou devolver a caixa. Miguel já tinha saído da cidade.'},
 {'visual':'building','text':'Davi baixou os olhos. Nunca corrigi a história, admitiu.'},
 {'visual':'drawing','text':'A carta não pedia dinheiro. Pedia que entregassem um desenho à filha dele.'}]},
7:{'title':'A menina que já tinha crescido','question':'Você atenderia uma ligação sobre um desenho da sua infância?','scenes':[
 {'visual':'drawing','text':'O último desenho era um presente. A menina que devia recebê-lo agora era adulta.'},
 {'visual':'room','text':'Na carta, Miguel escrevera o nome dela: Clara. Eva começou a procurar.'},
 {'visual':'building','text':'Davi encontrou um endereço antigo na ficha de morador. Foi a primeira ajuda sem desculpas.'},
 {'visual':'door','text':'Três tentativas depois, Clara atendeu o telefone. Lia explicou a caixa.'},
 {'visual':'room','text':'Meu pai morreu no inverno passado, ela contou. Achei que não tivesse guardado nada meu.'},
 {'visual':'drawing','text':'Então Lia virou o papel. Atrás, havia uma mensagem que ninguém tinha lido.'}]},
8:{'title':'O desenho finalmente entregue','question':'Qual lembrança da sua família você gostaria de preservar?','scenes':[
 {'visual':'drawing','text':'O presente chegou tarde. A mensagem atrás do desenho ainda podia encontrar Clara.'},
 {'visual':'room','text':'Miguel escrevera: você disse que nossa casa precisava de uma porta só sua. Então eu desenhei uma.'},
 {'visual':'drawing','text':'A porta a mais nunca fora um segredo do prédio. Era uma invenção de pai e filha.'},
 {'visual':'building','text':'Davi escreveu o que tinha feito. Clara recebeu a carta, sem prometer perdão.'},
 {'visual':'door','text':'Na semana seguinte, Lia e Eva entregaram a caixa pessoalmente.'},
 {'visual':'room','text':'Clara abraçou o desenho. Dessa vez, ninguém guardou a história numa gaveta. Fim.'}]},
}


def caption(number,offer):
    import story_offers
    story=STORIES[number]
    return (story['scenes'][0]['text']+f"\nA chave do 12 · O último desenho · Capítulo {number-3} de 5: {story['title']}.\n"
            'Ficção original em animação 3D com narração sintética.\n'+
            ('Final deste arco.\n' if number==8 else 'Continua no próximo capítulo.\n')+
            story['question']+'\n#historias #animacao3d #suspense #conteudogeradoporia'+story_offers.caption(offer))
