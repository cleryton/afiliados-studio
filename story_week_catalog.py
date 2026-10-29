"""Finite original sequel; global episode numbers preserve posting order."""
NUMBERS=tuple(range(1,16))
WEEK_NUMBERS=tuple(range(2,9))
NEXT_NUMBERS=tuple(range(9,16))
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

# Standalone microdramas: a new viewer can understand each complete story.
NEW_STORIES={
9:{'title':'A chave na mão errada','hooks':['A chave estava certa. A visita, não.','Lia abriu a porta errada.'],
 'question':'Você já confundiu um convite com uma obrigação?','scenes':[
 ('key','Lia encontrou uma chave na própria bolsa.','hook'),
 ('door','Era a cópia de Eva. Lia chegou sem avisar, carregando compras e soluções.','setup'),
 ('room','Eva não queria uma visita naquele dia. Lia ouviu isso como uma rejeição.','turn'),
 ('key','Ela colocou a chave na mesa. Então por que você me deu isto?','conflict'),
 ('room','Para você saber que pode entrar. Não para achar que precisa me salvar, respondeu Eva.','reveal'),
 ('door','Lia levou as compras de volta. No sábado, tocou a campainha. Eva abriu sorrindo.','payoff')]},
10:{'title':'A caixa que ninguém buscava','hooks':['Davi guardou a caixa por vinte anos.','Ninguém veio buscar aquela caixa.'],
 'question':'Que objeto seu conta uma história que quase ninguém conhece?','scenes':[
 ('building','Davi ia embora. A caixa continuaria ali.','hook'),
 ('room','No último dia como porteiro, ele pediu que Lia jogasse fora um velho caderno.','setup'),
 ('drawing','Entre as folhas, Eva encontrou desenhos do prédio. Cada janela tinha uma data.','turn'),
 ('building','Davi desenhava uma janela sempre que um morador chegava. Nunca contou a ninguém.','reveal'),
 ('room','Na última página, havia apenas um retângulo vazio. Era a janela da casa para onde ele iria.','conflict'),
 ('drawing','Eva devolveu o caderno com um lápis. Faltava desenhar a chegada dele.','payoff')]},
11:{'title':'O desenho sem assinatura','hooks':['Eva quase jogou aquele desenho fora.','O desenho não tinha assinatura.'],
 'question':'Você guarda alguma coisa que fez quando era criança?','scenes':[
 ('drawing','Eva quase jogou aquele desenho fora.','hook'),
 ('room','A casa estava torta. As pessoas tinham braços enormes. Parecia um rabisco sem importância.','setup'),
 ('drawing','Lia reconheceu a casa. Era onde as duas nasceram, antes de serem separadas.','turn'),
 ('room','Eva procurou a assinatura da mãe. Encontrou apenas uma data e uma palavra: Eva.','reveal'),
 ('drawing','A mãe não fizera o desenho. Guardara o primeiro desenho da filha que não pôde acompanhar.','conflict'),
 ('room','Eva comprou uma moldura simples. Pela primeira vez, assinou o próprio nome sem pedir desculpas.','payoff')]},
12:{'title':'A visita de cinco minutos','hooks':['Lia pediu cinco minutos. Eva ofereceu silêncio.','Ela só precisava ficar ali.'],
 'question':'O que faz você se sentir acolhido?','scenes':[
 ('door','Lia pediu só cinco minutos.','hook'),
 ('room','Chegou dizendo que estava tudo bem. Eva colocou duas xícaras na mesa, sem perguntar nada.','setup'),
 ('key','Lia girava a chave nas mãos. Tinha ensaiado uma explicação durante todo o caminho.','conflict'),
 ('room','Não precisa contar hoje, disse Eva. Lia finalmente parou de sorrir.','turn'),
 ('door','Cinco minutos viraram uma hora. Nenhum problema foi resolvido naquele apartamento.','reveal'),
 ('room','Quando foi embora, Lia já não precisava fingir que conseguiria resolver tudo sozinha.','payoff')]},
13:{'title':'A porta que ficou aberta','hooks':['Davi voltou. A porta estava aberta.','A despedida tinha sido cedo demais.'],
 'question':'Qual gesto pequeno fez diferença para você?','scenes':[
 ('door','Davi voltou. A porta estava aberta.','hook'),
 ('building','Ele esquecera um molho de chaves na antiga portaria. Esperava encontrar o prédio vazio.','setup'),
 ('room','Lia e Eva estavam sentadas no chão, entre caixas. O novo porteiro ainda não chegara.','turn'),
 ('key','Davi pegou as chaves e começou a explicar como consertar a fechadura do depósito.','conflict'),
 ('room','Eva interrompeu: nós sabemos. A cadeira é para você. Queríamos nos despedir direito.','reveal'),
 ('building','Pela primeira vez em tantos anos, Davi entrou naquele prédio sem precisar trabalhar.','payoff')]},
14:{'title':'A cópia que faltava','hooks':['Eva devolveu a chave antes da mudança.','A mudança não era uma despedida.'],
 'question':'Para você, o que transforma uma casa em um lugar de encontro?','scenes':[
 ('key','Eva devolveu a chave antes da mudança.','hook'),
 ('room','Lia não perguntou nada. A irmã estava levando caixas para uma casa menor, longe do prédio.','setup'),
 ('door','No dia seguinte, Lia apareceu para ajudar e deixou o envelope sobre a mesa.','conflict'),
 ('key','Dentro havia outra chave. A etiqueta dizia apenas: a minha.','turn'),
 ('room','Se você não morar mais aqui, pode me visitar lá, explicou Lia. Eva riu e chorou ao mesmo tempo.','reveal'),
 ('door','A mudança terminou naquela tarde. As duas combinaram o café do sábado no endereço novo.','payoff')]},
15:{'title':'O lugar no desenho','hooks':['No desenho, Lia não aparecia.','A casa tinha uma pessoa a menos.'],
 'question':'Qual lembrança merece ganhar espaço na sua casa?','scenes':[
 ('drawing','No desenho, Lia não aparecia.','hook'),
 ('room','Era a casa nova de Eva. Havia plantas, duas xícaras e um cachorro que ela ainda não tinha.','setup'),
 ('drawing','Lia brincou: até o cachorro imaginário ganhou lugar. Eva pediu que olhasse de novo.','conflict'),
 ('door','A porta estava aberta. No caminho, havia uma figura pequena carregando uma caixa.','turn'),
 ('room','Eu ainda não terminei você, disse Eva. Não sei desenhar alguém chegando para ficar.','reveal'),
 ('drawing','Lia pegou um lápis. Então desenha a caixa. Eu seguro. E as duas terminaram a casa juntas.','payoff')]},
}
for _number,_story in NEW_STORIES.items():
    STORIES[_number]={**_story,'arc':'Pequenos segredos do 12','arc_number':_number-8,'arc_total':7,
                     'standalone':True,'scenes':[{'visual':v,'text':t,'beat':b} for v,t,b in _story['scenes']]}


def caption(number,offer,story=None):
    import story_offers
    story=story or STORIES[number]
    if story.get('standalone'):
        return (story['scenes'][0]['text']+f"\nPequenos segredos do 12 · História {story['arc_number']} de 7: {story['title']}.\n"
                'Uma história completa de ficção original. Animação 3D e voz sintética.\n'+story['question']+
                '\n#historias #animacao3d #dramafamiliar #conteudogeradoporia'+story_offers.caption(offer))
    return (story['scenes'][0]['text']+f"\nA chave do 12 · O último desenho · Capítulo {number-3} de 5: {story['title']}.\n"
            'Ficção original em animação 3D com narração sintética.\n'+
            ('Final deste arco.\n' if number==8 else 'Continua no próximo capítulo.\n')+
            story['question']+'\n#historias #animacao3d #suspense #conteudogeradoporia'+story_offers.caption(offer))
