"""Four original, independent stories for the local 2D cartoon collection."""

STORIES = [
    {
        'key': 'cat', 'title': 'O gato e a última estrela', 'genre': 'Fantasia',
        'accent': '#ffd778', 'background': '#172745',
        'scenes': [
            'A última estrela do céu sumiu. E o gato Nico estava brilhando.',
            'Nico encontrara a estrela presa na antena. Guardou a luz na toca para iluminar o jantar.',
            'Naquela noite, um barquinho ficou sem a estrela que seguia para voltar ao porto.',
            'Do telhado, Nico viu o barco rodando no escuro. Puxou a estrela para fora, mas ela não conseguia subir.',
            'Ele escalou a chaminé mais alta e soltou a luz. A estrela voltou para o céu; o barco encontrou o cais.',
            'De manhã, havia um peixe na porta da toca. Nico ganhou seu jantar. E deixou a janela aberta para ver a estrela.',
        ],
    },
    {
        'key': 'robot', 'title': 'O pão de domingo', 'genre': 'Comédia delicada',
        'accent': '#f9c477', 'background': '#f1dfc7',
        'scenes': [
            'O robô padeiro recebeu um pedido impossível: pão com gosto de domingo.',
            'Ele mediu açúcar, farinha e até a temperatura da rua. A cliente provou e balançou a cabeça.',
            'Na terceira tentativa, o robô desligou as máquinas. Pela janela, viu a cliente sentada com duas xícaras.',
            'Ela contou que o pai fazia pães tortos e queimava uma pontinha. Era isso que tentava lembrar.',
            'O robô assou um pão sem usar a régua. Deixou uma pontinha dourar a mais e levou a bandeja até a mesa.',
            'A cliente dividiu o pão e ofereceu uma xícara. O robô não podia beber. Mas ficou para ouvir a história.',
        ],
    },
    {
        'key': 'umbrella', 'title': 'O guarda-chuva ao contrário', 'genre': 'Comédia fantástica',
        'accent': '#f37567', 'background': '#d0e8e2',
        'scenes': [
            'Quando Bia abriu o guarda-chuva, começou a chover do lado de dentro.',
            'Na rua, o céu estava limpo. Ela fechou o tecido, abriu outra vez e recebeu um novo banho.',
            'Um senhor no ponto riu e mostrou a etiqueta: um guarda-chuva para dias ao contrário.',
            'Bia ia jogá-lo fora quando viu os vasos secos da vizinha, que estava viajando.',
            'Segurou o guarda-chuva sobre cada vaso. A água caiu só ali, sem molhar as roupas no varal.',
            'Uma semana depois, a vizinha voltou e encontrou flores. Bia guardou o guarda-chuva ao lado do regador.',
        ],
    },
    {
        'key': 'lighthouse', 'title': 'O farol de bolso', 'genre': 'Aventura',
        'accent': '#f3d995', 'background': '#192e42',
        'scenes': [
            'O farol perdeu a luz na noite em que o filho do faroleiro voltava de barco.',
            'Trocar a lâmpada não adiantou. A tempestade tinha cortado a energia da ilha inteira.',
            'No bolso do casaco, o faroleiro encontrou uma lanterna. Da praia, era só um ponto perdido na chuva.',
            'Então, percorreu a vila pedindo ajuda. Os vizinhos vieram com lanternas, espelhos e tampas brilhantes.',
            'Juntos, apontaram as luzes para a entrada do porto. O filho reconheceu as casas e fez a curva.',
            'Quando o barco encostou, o pai ainda tremia. O filho abraçou os vizinhos antes de perguntar quem tivera aquela ideia.',
        ],
    },
]


def caption(story):
    return (f"{story['title']} | Uma história completa de Novelitas.\n\n"
            'Ficção original em animação 2D. Personagens e cenários desenhados por código, '
            'com assistência de IA. Narração sintética em português.\n\n'
            '#historias #animacao2d #ficcao #conteudogeradoporia')
