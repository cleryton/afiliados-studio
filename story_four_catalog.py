"""Seven complete, original neighborhood mysteries for the fourth daily slot."""

RAW = [
('As três batidas', 'Eva ouviu três batidas numa porta que ninguém usava.', 'Que som faz você lembrar de alguém?', [
 ('door', 'A antiga sala do prédio estava fechada havia meses. Naquela tarde, o barulho voltou duas vezes.'),
 ('building', 'Davi tinha a chave, mas hesitou em entregá-la. Lia achou que ele escondia alguma coisa.'),
 ('key', 'Eva pediu que abrissem juntos. Dentro, encontraram uma janela solta batendo no armário da parede.'),
 ('drawing', 'No armário havia um desenho antigo. No verso, o pedido de uma menina para aprender a consertar coisas.'),
 ('room', 'Era o pedido da filha de Davi, hoje morando longe. Ele fotografou o papel e ligou para ela antes de fechar a janela.')]),
('O presente devolvido', 'Lia encontrou o presente de aniversário do lado de fora.', 'Como você costuma descobrir do que alguém realmente precisa?', [
 ('door', 'A caixa estava intacta, com o laço que ela mesma fizera. Eva nem tinha aberto o pacote.'),
 ('room', 'Lia entrou pronta para discutir. A irmã mostrou os móveis cobertos: uma infiltração molhara o quarto durante a noite.'),
 ('drawing', 'Eva desenhara num papel a ordem das coisas que precisava retirar. O presente era o único objeto ainda seco.'),
 ('room', 'Lia guardou a caixa e ajudou a esvaziar o cômodo. Passaram a tarde levando livros para longe da parede.'),
 ('door', 'À noite, Eva abriu o presente na casa da irmã. O laço estava amassado. Dessa vez, Lia sabia por quê.')]),
('A chave marcada', 'Alguém devolveu a chave de Eva com uma marca vermelha.', 'Você já confundiu um cuidado com uma ameaça?', [
 ('key', 'Eva emprestara a cópia a Davi para receber uma entrega. Agora havia tinta perto dos dentes da chave.'),
 ('room', 'Ela perguntou se alguém tentara entrar. Davi mostrou o próprio molho, todo marcado com pequenas cores.'),
 ('building', 'Depois de entregar uma encomenda na porta errada, ele começara a identificar cada cópia. Tinha marcado aquela por costume, sem perguntar.'),
 ('key', 'Davi pediu desculpas e ofereceu retirar a tinta. Eva preferiu guardar a marca, mas combinou que ninguém mudaria suas coisas sem avisar.'),
 ('door', 'Na entrega seguinte, Davi tocou a campainha e esperou. Eva abriu a porta antes que ele precisasse usar a cópia.')]),
('O desenho sob a mesa', 'O desenho perdido de Lia apareceu debaixo de outra assinatura.', 'Como você corrigiria um erro que beneficiou você?', [
 ('drawing', 'Eva levara dois trabalhos para a exposição do bairro. Na pressa, colocara o próprio nome em ambos.'),
 ('room', 'Lia viu a fotografia da montagem e reconheceu a janela torta que desenhara. Pediu que a irmã olhasse o verso do papel.'),
 ('drawing', 'Estavam lá a data e as iniciais de Lia. Eva percebeu o erro quando a exposição já havia começado.'),
 ('building', 'Em vez de esperar o fim da mostra, voltou ao salão e explicou a troca a quem organizava as etiquetas.'),
 ('room', 'No dia seguinte, as duas foram juntas. Eva apontou o quadro para uma visitante e apresentou a autora que estava ao seu lado.')]),
('A visita sem flores', 'Davi voltou de uma visita carregando o mesmo buquê.', 'Que gesto simples você gostaria de receber numa visita?', [
 ('building', 'Ele atravessou o corredor sem dizer nada. Lia pensou que a filha tivesse recusado recebê-lo.'),
 ('room', 'Davi contou que ela abrira a porta e pedira que levasse as flores de volta. O gato derrubava todos os vasos.'),
 ('drawing', 'Sobre a mesa, ele abriu um desenho que a filha fizera do primeiro apartamento. Queria aprender a copiá-lo num cartão.'),
 ('room', 'Eva ofereceu um lápis e ficou ao lado enquanto ele tentava. Davi apagou uma janela, riu e começou outra vez.'),
 ('door', 'Na visita seguinte, levou o cartão e o almoço combinado. A filha o recebeu com uma moldura vazia esperando sobre a mesa.')]),
('A luz do apartamento vazio', 'A luz do apartamento vazio acendeu todas as noites.', 'Qual lembrança você levaria de uma casa antiga?', [
 ('building', 'Lia viu o clarão pela janela do corredor. O antigo morador já havia entregue as chaves.'),
 ('key', 'Davi conferiu o registro. Só a filha do morador ainda tinha autorização para retirar o que faltava.'),
 ('door', 'Quando se encontraram à porta, ela mostrou uma luminária com temporizador. O pai a deixara ligada antes de sair.'),
 ('drawing', 'Eva perguntou se podia desenhar a janela iluminada antes de desmontarem tudo. A filha esperou sentada no corredor.'),
 ('room', 'A luz não acendeu na noite seguinte. Na casa nova, o desenho ficou ao lado da luminária que finalmente tinha voltado para a família.')]),
('O envelope para domingo', 'Eva abriu no sábado um envelope escrito para domingo.', 'Você guarda cartas para reler em outra época?', [
 ('drawing', 'A letra era dela, mas o papel estava entre as coisas da mãe. Dentro havia uma casa desenhada com duas portas.'),
 ('room', 'Lia encontrou a data no canto. Era de uma atividade da infância: escrever uma carta para si mesma vinte anos depois.'),
 ('drawing', 'Eva lera a primeira frase como uma despedida. Continuou: se você esqueceu de desenhar, ainda dá tempo de voltar.'),
 ('room', 'As irmãs passaram o sábado tentando refazer a casa. Cada uma lembrava de uma janela diferente.'),
 ('door', 'No domingo, Eva guardou os três desenhos no mesmo envelope. Escreveu uma nova data e deixou o lápis do lado de fora.')]),
]

FOUR_STORIES = {}
for number, (title, hook, question, rest) in enumerate(RAW, 30):
    FOUR_STORIES[number] = {
        'title':title, 'question':question, 'hooks':[hook], 'arc':'Mistérios da vizinhança',
        'arc_number':number-29, 'arc_total':7, 'standalone':True,
        'scenes':[{'visual':rest[0][0], 'text':hook, 'beat':'hook'}] +
                 [{'visual':v,'text':t,'beat':b} for (v,t),b in zip(rest,('setup','conflict','turn','reveal','payoff'))],
    }
