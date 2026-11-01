"""Fourteen new, complete microdramas for the additional daily slots."""

RAW = [
('O bilhete no elevador', 'Um bilhete mandava Lia fazer menos barulho.', 'Como você pediria ajuda sem expor sua dificuldade?', [
 ('door', 'Lia leu o recado no elevador e preparou uma resposta atravessada.'),
 ('building', 'Davi pediu que esperasse. O vizinho do andar de baixo trabalhava à noite e dormia durante as mudanças.'),
 ('room', 'Ela voltou ao apartamento, certa de que teria de cancelar a chegada dos móveis.'),
 ('drawing', 'Eva desenhou um horário numa folha. Duas horas de silêncio, depois duas horas para carregar as caixas.'),
 ('door', 'O vizinho trouxe uma garrafa de água quando o caminhão chegou. No elevador, ficou apenas o horário combinado.')]),
('A xícara trincada', 'Eva escondeu a xícara quebrada antes de Lia chegar.', 'Há algum objeto que você prefere reparar a substituir?', [
 ('room', 'Era a única peça do jogo da mãe. A alça se partira enquanto ela lavava a louça.'),
 ('key', 'Lia encontrou a gaveta aberta. Eva esperava uma bronca, mas a irmã pediu todos os pedaços.'),
 ('room', 'Durante a tarde, tentaram encaixar a alça. A marca continuaria aparecendo.'),
 ('drawing', 'Eva desenhou pequenas flores num cartão e colocou a xícara ao lado, agora como porta-lápis.'),
 ('room', 'No café seguinte, cada uma usou uma caneca diferente. A peça da mãe continuou na mesa, guardando os lápis.')]),
('O desenho virado para a parede', 'Lia virou o desenho antes da visita.', 'Que parte de uma lembrança você prefere guardar só para você?', [
 ('drawing', 'Era um retrato da mãe, ainda sem rosto. Eva entendeu o gesto como vergonha.'),
 ('room', 'Na visita, elogiou o quadro em voz alta. Lia ficou quieta e mudou de assunto.'),
 ('door', 'Depois que todos saíram, Eva perguntou por que a irmã escondia o desenho.'),
 ('drawing', 'Porque ainda é meu rascunho, respondeu Lia. Eu não estava pronta para mostrar.'),
 ('room', 'Eva pediu desculpas. Na semana seguinte, bateu à porta com duas molduras e perguntou quais desenhos podia olhar.')]),
('A sacola que se abriu', 'A sacola de Davi rasgou no corredor.', 'Qual ajuda você já recebeu sem precisar pedir?', [
 ('building', 'Caíram no chão retalhos de tecido. Ele correu para recolher tudo antes que alguém visse.'),
 ('room', 'Eva ajudou em silêncio. Davi contou que estava aprendendo a costurar, escondido dos amigos.'),
 ('drawing', 'Lia pediu um pedaço de papel e desenhou uma bolsa simples, com a alça reforçada.'),
 ('room', 'Ele apontou uma emenda torta. As duas perguntaram se podiam encomendar bolsas para as próprias mudanças.'),
 ('door', 'Davi voltou uma semana depois com três bolsas. A terceira era dele, com os retalhos guardados à vista.')]),
('O relógio que não precisava voltar', 'Lia deu corda ao relógio e Eva pediu que parasse.', 'Você precisa conservar tudo para preservar uma lembrança?', [
 ('room', 'O relógio da mãe estava parado havia meses. Lia achou que consertá-lo seria uma surpresa.'),
 ('key', 'Eva tirou a chave da mão dela. Aquele som a acordara durante toda a infância.'),
 ('room', 'Lia respondeu que não queria deixar as coisas da mãe desaparecerem. A irmã puxou uma cadeira.'),
 ('drawing', 'Juntas, desenharam o relógio numa folha e anotaram as histórias que lembravam dele.'),
 ('room', 'O objeto foi para uma caixa. A folha ficou na parede, e o café continuou sem as badaladas.')]),
('A cadeira com nome', 'Davi escreveu o nome numa cadeira emprestada.', 'Como você cuida de algo que pertence a outra pessoa?', [
 ('building', 'Lia pegara a cadeira para receber visitas. Viu a etiqueta e achou que ele não confiava nela.'),
 ('room', 'Quando foi devolver, encontrou outras três peças com nomes diferentes na casa dele.'),
 ('key', 'Davi explicou que os vizinhos haviam emprestado os móveis durante sua mudança. Tinha medo de trocar as devoluções.'),
 ('drawing', 'Lia desenhou uma pequena lista com cada peça e seu dono. Davi soltou a etiqueta da cadeira.'),
 ('door', 'Na manhã seguinte, devolveram tudo juntos. A lista terminou com uma linha nova: mesa para o café, de todos.')]),
('O envelope sem carta', 'O envelope de Eva estava vazio.', 'Qual foi a primeira mensagem que você guardou de alguém?', [
 ('room', 'Lia procurou uma folha no chão. A irmã pediu que olhasse o selo e a letra do endereço.'),
 ('drawing', 'Era a primeira correspondência que a mãe adotiva de Eva recebera com o nome escrito pela filha.'),
 ('room', 'A carta se perdera. Eva ensaiou jogar o envelope fora, porque a história parecia incompleta.'),
 ('drawing', 'Lia trouxe uma folha nova. Eva desenhou a mesa onde aprendera a escrever e colocou a lembrança dentro.'),
 ('room', 'No verso do envelope, anotou a data daquele café. Agora havia duas histórias para guardar no mesmo lugar.')]),
('A caixa de endereços', 'Davi encontrou o próprio endereço numa caixa de doações.', 'Que coisa comum pode fazer falta numa mudança?', [
 ('building', 'Lia separava papéis antigos da portaria. Uma caixa pequena estava marcada para descarte.'),
 ('room', 'Dentro havia etiquetas que os vizinhos escreveram quando ele se mudou. Cada uma tinha uma letra diferente.'),
 ('drawing', 'Lia pensou em fotografar tudo. Davi pediu um cartão em branco e começou a copiar os nomes.'),
 ('key', 'Ele não precisava conservar os endereços antigos. Queria lembrar quem o ajudara a chegar à casa nova.'),
 ('door', 'A caixa voltou com Davi. No sábado, ele entregou os primeiros convites para um café no endereço certo.')]),
('A moldura sem fotografia', 'Eva pendurou uma moldura vazia.', 'O que você gostaria de registrar do seu presente?', [
 ('room', 'Lia ofereceu uma fotografia antiga da família. A irmã recusou, e o silêncio ficou pesado.'),
 ('drawing', 'Havia uma folha branca dentro da moldura. Eva queria desenhar a própria casa, mas ainda não sabia por onde começar.'),
 ('room', 'Lia contou que achara que a irmã estivesse apagando o passado. Eva respondeu que tentava registrar o presente.'),
 ('drawing', 'Cada uma desenhou um objeto da mesa. A xícara de Lia ficou enorme; a planta de Eva, muito pequena.'),
 ('room', 'Guardaram os dois desenhos na moldura. A fotografia antiga ganhou outro lugar, ao lado, sem precisar disputar espaço.')]),
('Os dois nomes da porta', 'Lia apagou um nome da etiqueta da porta.', 'Que nome faz você se sentir em casa?', [
 ('door', 'Estava ajudando na mudança de Eva. A etiqueta tinha o nome antigo da irmã e o que ela passara a usar.'),
 ('room', 'Eva segurou o papel antes de ir para o lixo. Lia disse que só queria deixar a entrada organizada.'),
 ('drawing', 'A irmã contou quem a chamara de cada jeito. Nenhum nome estava ali por engano.'),
 ('key', 'Lia buscou outra etiqueta e perguntou como ela queria ser recebida naquela casa.'),
 ('door', 'Eva escreveu os dois nomes outra vez. Lia colou o papel devagar e tocou a campainha para estrear.')]),
('O recado apagado', 'Eva apagou uma frase que Lia levava meses escrevendo.', 'Você costuma perguntar antes de reorganizar as coisas de alguém?', [
 ('room', 'O quadro da cozinha parecia cheio de riscos. Eva limpou tudo para ajudar antes do jantar.'),
 ('drawing', 'Lia ficou olhando a superfície vazia. A frase era uma tentativa de encontrar as palavras para uma carta.'),
 ('room', 'Eva ofereceu várias versões. Nenhuma soava como o que a irmã queria dizer.'),
 ('drawing', 'Então parou de sugerir. Entregou o marcador e ficou ao lado enquanto Lia recomeçava a primeira linha.'),
 ('room', 'No canto do quadro, escreveram juntas um pedido menor: antes de apagar, pergunte. A carta ficou pronta depois do jantar.')]),
('O guarda-chuva devolvido', 'Davi devolveu um guarda-chuva num dia de sol.', 'Algum favor pequeno mudou a sua semana?', [
 ('building', 'Esperou na portaria com o objeto seco debaixo do braço. Lia achou que ele tivesse confundido o dia da visita.'),
 ('door', 'Na semana anterior, Eva emprestara o guarda-chuva sem perguntar quando ele voltaria.'),
 ('room', 'Davi contou que, na casa nova, ainda tinha vergonha de pedir coisas aos vizinhos.'),
 ('key', 'Eva pendurou o guarda-chuva junto à porta. Disse que não precisava esperar uma desculpa para aparecer.'),
 ('door', 'Ele voltou para casa sem o objeto. Dois dias depois, tocou a campainha levando apenas pão para o café.')]),
('O café que ficou para depois', 'Lia cancelou o café e deixou as duas xícaras prontas.', 'Como você demonstra cuidado quando precisa de tempo sozinho?', [
 ('room', 'Eva chegou antes de ler a mensagem. Viu a mesa posta e pensou que a irmã não queria recebê-la.'),
 ('door', 'Lia abriu a porta ainda de casaco. Tinha passado a noite tentando resolver uma mudança no trabalho.'),
 ('room', 'Pediu uma tarde sozinha. Eva quase perguntou o que havia feito de errado, mas guardou a pergunta.'),
 ('drawing', 'Na manhã seguinte, encontrou um bilhete de Lia com duas datas livres, sem uma longa justificativa.'),
 ('room', 'Escolheram o sábado. Quando Eva chegou, as xícaras eram as mesmas; dessa vez, as duas tinham tempo para sentar.')]),
('O primeiro risco', 'Eva assinou uma folha antes de desenhar qualquer coisa.', 'Qual começo você está adiando por medo de não ficar bom?', [
 ('drawing', 'Lia perguntou se aquela era a obra pronta. A irmã disse que estava tentando parar de esconder os rascunhos.'),
 ('room', 'Havia folhas amassadas debaixo da mesa. Em todas, Eva começara pela mesma janela e desistira no telhado.'),
 ('drawing', 'Lia abriu uma folha e mostrou a parte que gostava. Eva decidiu continuar aquele desenho, com a janela torta.'),
 ('room', 'As duas desenharam em silêncio. Ninguém transformou o papel numa competição ou numa lembrança da mãe.'),
 ('drawing', 'Eva terminou a casa e colocou a data ao lado da assinatura. Guardou também a primeira tentativa, desta vez sem amassar.')]),
]

EXTRA_STORIES = {}
for number, (title, hook, question, rest) in enumerate(RAW, 16):
    beats = ('setup', 'conflict', 'turn', 'reveal', 'payoff')
    EXTRA_STORIES[number] = {
        'title': title, 'question': question, 'hooks': [hook],
        'arc': 'Outras portas do 12', 'arc_number': number - 15, 'arc_total': 14, 'standalone': True,
        'scenes': [{'visual': rest[0][0], 'text': hook, 'beat': 'hook'}] +
                  [{'visual': visual, 'text': text, 'beat': beat} for (visual, text), beat in zip(rest, beats)],
    }
