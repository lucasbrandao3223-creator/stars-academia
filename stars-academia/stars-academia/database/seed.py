"""Popula o banco com os dados da STARS Academia e um histórico de demonstração.

Tudo é gerado a partir da data de hoje, então o sistema sempre abre com dados
"vivos": alunos com plano ativo, planos vencendo, check-ins dos últimos dias e
fichas de treino montadas pelos personais.
"""
import random
from datetime import date, datetime, time, timedelta

from models.academia import Academia, HorarioFuncionamento
from models.matricula import Checkin, Matricula
from models.plano import Plano
from models.treino import Exercicio, ItemTreino, Treino, TreinoRealizado
from models.usuario import Administrador, Aluno, Personal
from repositories import (AcademiaRepositorio, CheckinRepositorio, ExercicioRepositorio,
                          MatriculaRepositorio, PlanoRepositorio, TreinoRealizadoRepositorio, TreinoRepositorio,
                          UsuarioRepositorio)
from utils import somar_meses

SENHA_PADRAO = "123456"

ACADEMIA = {
    "nome": "STARS Academia",
    "slogan": "Treine como uma estrela.",
    "descricao": "Musculação, aeróbico e acompanhamento de personal trainer em um espaço climatizado de "
                 "1.200 m², com equipamentos novos, vestiários completos e uma equipe que treina junto com você.",
    "endereco": "Av. das Estrelas, 500 - Centro",
    "cidade": "São Paulo - SP",
    "telefone": "1132450500",
    "whatsapp": "11987650500",
    "instagram": "@starsacademia",
}

# segunda a sexta 6h-23h, sábado 8h-18h, domingo 8h-12h
HORARIOS = [(d, "06:00", "23:00") for d in range(5)] + [(5, "08:00", "18:00"), (6, "08:00", "12:00")]

GRUPOS = ["Peito", "Costas", "Ombros", "Bíceps", "Tríceps", "Pernas", "Glúteos", "Abdômen", "Cardio"]

EXERCICIOS = [
    ("Supino reto com barra", "Peito", "Barra e banco", "Desça a barra até o meio do peito e empurre sem tirar o quadril do banco."),
    ("Supino inclinado com halteres", "Peito", "Halteres e banco inclinado", "Banco a 30°, cotovelos levemente para dentro."),
    ("Crucifixo na máquina", "Peito", "Peck deck", "Movimento controlado, sem bater os pesos."),
    ("Crossover", "Peito", "Polia", "Cruze as mãos à frente do corpo apertando o peitoral."),
    ("Flexão de braço", "Peito", "Peso corporal", "Corpo alinhado, desça até quase encostar o peito no chão."),
    ("Puxada frontal", "Costas", "Pulley", "Puxe a barra até o queixo levando os cotovelos para baixo."),
    ("Remada curvada", "Costas", "Barra", "Tronco inclinado e coluna neutra; puxe a barra até o umbigo."),
    ("Remada baixa", "Costas", "Polia baixa", "Estufe o peito e aproxime as escápulas no final."),
    ("Pulldown com corda", "Costas", "Polia alta", "Braços quase estendidos, leve a corda até as coxas."),
    ("Barra fixa", "Costas", "Barra fixa", "Pegada pronada; suba até o queixo passar a barra."),
    ("Desenvolvimento com halteres", "Ombros", "Halteres", "Empurre os halteres acima da cabeça sem travar os cotovelos."),
    ("Elevação lateral", "Ombros", "Halteres", "Suba até a altura dos ombros com cotovelos levemente flexionados."),
    ("Elevação frontal", "Ombros", "Halteres", "Alterne os braços, sem balançar o tronco."),
    ("Face pull", "Ombros", "Polia com corda", "Puxe a corda em direção ao rosto abrindo os cotovelos."),
    ("Rosca direta", "Bíceps", "Barra W", "Cotovelos colados ao corpo durante todo o movimento."),
    ("Rosca martelo", "Bíceps", "Halteres", "Pegada neutra, palmas viradas para o corpo."),
    ("Rosca Scott", "Bíceps", "Banco Scott", "Desça devagar até quase estender os braços."),
    ("Tríceps pulley", "Tríceps", "Polia alta", "Cotovelos parados ao lado do corpo; estenda totalmente."),
    ("Tríceps francês", "Tríceps", "Halter", "Halter atrás da cabeça, cotovelos apontando para cima."),
    ("Mergulho no banco", "Tríceps", "Banco", "Desça até os cotovelos formarem 90°."),
    ("Agachamento livre", "Pernas", "Barra e gaiola", "Joelhos na direção dos pés; desça até a coxa ficar paralela ao chão."),
    ("Leg press 45°", "Pernas", "Leg press", "Não tire o quadril do encosto e não trave os joelhos."),
    ("Cadeira extensora", "Pernas", "Cadeira extensora", "Segure 1 segundo no alto."),
    ("Mesa flexora", "Pernas", "Mesa flexora", "Quadril colado no banco durante o movimento."),
    ("Stiff", "Pernas", "Barra", "Pernas quase estendidas; desça a barra rente às pernas."),
    ("Afundo", "Pernas", "Halteres", "Passo largo, joelho de trás quase encosta no chão."),
    ("Panturrilha em pé", "Pernas", "Máquina de panturrilha", "Amplitude total, pausa em cima."),
    ("Elevação pélvica", "Glúteos", "Barra e banco", "Suba o quadril contraindo os glúteos; não arqueie a lombar."),
    ("Cadeira abdutora", "Glúteos", "Cadeira abdutora", "Abra as pernas de forma controlada."),
    ("Glúteo na polia", "Glúteos", "Polia baixa com tornozeleira", "Estenda o quadril para trás sem girar o tronco."),
    ("Abdominal supra", "Abdômen", "Colchonete", "Tire só as escápulas do chão."),
    ("Prancha", "Abdômen", "Peso corporal", "Corpo reto da cabeça aos pés, abdômen contraído."),
    ("Abdominal infra", "Abdômen", "Banco", "Eleve as pernas sem embalo."),
    ("Esteira", "Cardio", "Esteira", "Caminhada ou corrida na intensidade combinada com o personal."),
    ("Bicicleta ergométrica", "Cardio", "Bicicleta", "Ajuste o banco na altura do quadril."),
    ("Elíptico", "Cardio", "Elíptico", "Mantenha a postura ereta."),
]

PLANOS = [
    ("Mensal", 1, 119.90, "Sem fidelidade. Musculação e aeróbico liberados."),
    ("Trimestral", 3, 104.90, "3 meses com desconto. Avaliação física inclusa."),
    ("Semestral", 6, 94.90, "6 meses. Avaliação física a cada 3 meses."),
    ("Anual", 12, 84.90, "O melhor preço. Avaliações trimestrais e 1 mês de personal grátis."),
]

ADMIN = ("Ricardo Moura", "admin@stars.com", "11987650500")

# (nome, e-mail, telefone, CREF, especialidade, anos de experiência, bio)
PERSONAIS = [
    ("Carla Mendes", "personal@stars.com", "11987651001", "012345-G/SP", "Hipertrofia e força", 9,
     "Formada em Educação Física pela USP, pós-graduada em musculação e treinamento de força. Monta treinos "
     "periodizados e acompanha a evolução de carga de perto."),
    ("Diego Ramos", "diego@stars.com", "11987651002", "023456-G/SP", "Emagrecimento e funcional", 6,
     "Especialista em treino funcional e HIIT. Ajuda quem quer perder gordura com treinos curtos, intensos e "
     "divertidos, sempre junto com mudança de hábitos."),
    ("Juliana Prado", "juliana@stars.com", "11987651003", "034567-G/SP", "Glúteos e treino feminino", 7,
     "Especialista em membros inferiores e em acompanhar quem está começando. Treinos seguros, com técnica "
     "bem feita antes de qualquer carga."),
    ("Rafael Tavares", "rafael.t@stars.com", "11987651004", "045678-G/SP", "Powerlifting e força máxima", 11,
     "Atleta de powerlifting com títulos estaduais. Ensina agachamento, supino e levantamento terra com "
     "foco em técnica e progressão segura."),
    ("Aline Fonseca", "aline@stars.com", "11987651005", "056789-G/SP", "Reabilitação e mobilidade", 8,
     "Trabalha junto com fisioterapeutas na volta aos treinos depois de lesões. Mobilidade, postura e "
     "fortalecimento sem dor."),
    ("Bruno Siqueira", "bruno.s@stars.com", "11987651006", "067890-G/SP", "Corrida e condicionamento", 5,
     "Corredor de maratona. Prepara alunos para provas de 5 km a 42 km com treino de força complementar."),
    ("Patrícia Nogueira", "patricia@stars.com", "11987651007", "078901-G/SP", "Terceira idade e saúde", 12,
     "Especialista em treinamento para pessoas acima de 60 anos: equilíbrio, força e autonomia no dia a dia."),
    ("Marcos Vieira", "marcos@stars.com", "11987651008", "089012-G/SP", "Calistenia e HIIT", 4,
     "Treina com o peso do próprio corpo: barra, paralela, pranchas e circuitos de alta intensidade."),
]

ALUNOS = [
    ("Lucas Aluno", "aluno@teste.com"), ("Gabriel Souza", "gabriel@teste.com"),
    ("Mariana Costa", "mariana@teste.com"), ("Pedro Henrique", "pedro@teste.com"),
    ("Beatriz Lima", "beatriz@teste.com"), ("Rafael Oliveira", "rafael@teste.com"),
    ("Larissa Gomes", "larissa@teste.com"), ("Matheus Santos", "matheus@teste.com"),
    ("Camila Rocha", "camila@teste.com"), ("João Victor", "joao@teste.com"),
    ("Fernanda Alves", "fernanda@teste.com"), ("Thiago Martins", "thiago@teste.com"),
    ("Amanda Ribeiro", "amanda@teste.com"), ("Bruno Carvalho", "bruno@teste.com"),
    ("Isabela Ferreira", "isabela@teste.com"), ("Felipe Araújo", "felipe@teste.com"),
    ("Letícia Barbosa", "leticia@teste.com"), ("Gustavo Pereira", "gustavo@teste.com"),
    ("Vitória Nunes", "vitoria@teste.com"), ("Eduardo Teixeira", "eduardo@teste.com"),
    ("Juliana Castro", "julianac@teste.com"), ("Rodrigo Melo", "rodrigo@teste.com"),
    ("Natália Dias", "natalia@teste.com"), ("André Moreira", "andre@teste.com"),
    ("Carolina Freitas", "carolina@teste.com"), ("Daniel Cardoso", "daniel@teste.com"),
    ("Sofia Azevedo", "sofia@teste.com"), ("Vinícius Rocha", "vinicius@teste.com"),
]

# Fichas de treino-modelo: (nome, [(exercício, séries, repetições, carga base, descanso)])
FICHAS = {
    "A": ("Treino A - Peito, Ombros e Tríceps", [
        ("Supino reto com barra", 4, "10-12", 30, 90), ("Supino inclinado com halteres", 3, "10-12", 14, 75),
        ("Crucifixo na máquina", 3, "12", 35, 60), ("Desenvolvimento com halteres", 3, "10", 12, 75),
        ("Elevação lateral", 3, "12-15", 6, 60), ("Tríceps pulley", 3, "12", 25, 60),
        ("Tríceps francês", 3, "10", 10, 60)]),
    "B": ("Treino B - Costas e Bíceps", [
        ("Puxada frontal", 4, "10-12", 45, 90), ("Remada curvada", 3, "10", 30, 90),
        ("Remada baixa", 3, "12", 40, 60), ("Pulldown com corda", 3, "12", 20, 60),
        ("Rosca direta", 3, "10-12", 20, 60), ("Rosca martelo", 3, "12", 10, 60),
        ("Prancha", 3, "40s", None, 45)]),
    "C": ("Treino C - Pernas e Glúteos", [
        ("Agachamento livre", 4, "8-10", 40, 120), ("Leg press 45°", 4, "12", 120, 90),
        ("Cadeira extensora", 3, "12-15", 35, 60), ("Mesa flexora", 3, "12", 30, 60),
        ("Stiff", 3, "10", 30, 75), ("Elevação pélvica", 4, "12", 50, 75),
        ("Panturrilha em pé", 4, "15", 40, 45)]),
}
CARDIO_FINAL = ("Esteira", 1, "20min", None, 0)


# Situação de matrícula de cada aluno (vai repetindo nessa ordem). O 1º aluno é o de demonstração.
CENARIOS = ["ativa", "ativa", "vencendo", "ativa", "cancelada", "vencendo", "ativa", "vencida",
            "renovada", "ativa", "vencida", "ativa"]

# Horários mais comuns de check-in (manhã cedo, almoço e fim da tarde)
HORAS_CHECKIN = [6, 7, 7, 8, 12, 17, 18, 18, 19, 19, 20, 21]

rnd = random.Random(2026)   # sorteio sempre igual, para o banco de exemplo sair sempre do mesmo jeito


def popular(conexao, relogio=datetime.now):
    """Cria todos os dados de exemplo. É chamado pelo init_db.py."""
    conexao.execute("PRAGMA synchronous = OFF")   # deixa a carga inicial mais rápida
    rnd.seed(2026)
    agora = relogio()

    academia = criar_academia(conexao)
    exercicios = criar_exercicios(conexao)
    planos = criar_planos(conexao)
    personais = criar_equipe(conexao)
    for numero, (nome, email) in enumerate(ALUNOS):
        criar_aluno(conexao, numero, nome, email, academia, planos, personais, exercicios, agora)


def criar_academia(conexao):
    academia = Academia(**ACADEMIA)
    for dia, abre, fecha in HORARIOS:
        academia.definir_horario(HorarioFuncionamento(dia, abre, fecha))
    return AcademiaRepositorio(conexao).salvar(academia)


def criar_exercicios(conexao):
    """Cria os grupos musculares e os exercícios. Devolve {nome do exercício: id}."""
    for grupo in GRUPOS:
        conexao.execute("INSERT INTO grupo_muscular (nome) VALUES (?)", (grupo,))
    conexao.commit()
    id_do_grupo = {}
    for linha in conexao.execute("SELECT id, nome FROM grupo_muscular"):
        id_do_grupo[linha["nome"]] = linha["id"]

    repositorio = ExercicioRepositorio(conexao)
    id_do_exercicio = {}
    for nome, grupo, equipamento, instrucoes in EXERCICIOS:
        ex = repositorio.salvar(Exercicio(nome=nome, grupo_muscular_id=id_do_grupo[grupo],
                                          equipamento=equipamento, instrucoes=instrucoes))
        id_do_exercicio[nome] = ex.id
    return id_do_exercicio


def criar_planos(conexao):
    repositorio = PlanoRepositorio(conexao)
    planos = []
    for nome, meses, preco, descricao in PLANOS:
        planos.append(repositorio.salvar(Plano(nome=nome, duracao_meses=meses, preco_mensal=preco,
                                               descricao=descricao)))
    return planos


def criar_equipe(conexao):
    """Cria o administrador e os personais. Devolve a lista de personais."""
    usuarios = UsuarioRepositorio(conexao)
    nome, email, telefone = ADMIN
    admin = Administrador(nome=nome, email=email, telefone=telefone)
    admin.definir_senha(SENHA_PADRAO)
    usuarios.salvar(admin)

    personais = []
    for nome, email, telefone, cref, especialidade, anos, bio in PERSONAIS:
        p = Personal(nome=nome, email=email, telefone=telefone, cref=cref, especialidade=especialidade,
                     bio=bio, anos_experiencia=anos)
        p.definir_senha(SENHA_PADRAO)
        personais.append(usuarios.salvar(p))
    return personais


def criar_aluno(conexao, numero, nome, email, academia, planos, personais, exercicios, agora):
    """Cria um aluno com matrícula, check-ins, fichas de treino e treinos realizados."""
    hoje = agora.date()
    demo = numero == 0      # aluno@teste.com, usado na apresentação

    # ---------- 1. o aluno ----------
    idade = rnd.randint(16, 52)
    aluno = Aluno(nome=nome, email=email, telefone="119" + str(rnd.randint(10000000, 99999999)),
                  data_nascimento=date(hoje.year - idade, rnd.randint(1, 12), rnd.randint(1, 28)),
                  objetivo=rnd.choice(Aluno.OBJETIVOS),
                  meta_semanal=4 if demo else rnd.randint(2, 5),
                  personal_id=personais[0].id if demo else personais[numero % len(personais)].id)
    if numero % 7 == 3:
        aluno.personal_id = None          # alguns alunos ainda sem personal
    aluno.definir_senha(SENHA_PADRAO)
    UsuarioRepositorio(conexao).salvar(aluno)

    # ---------- 2. matrículas ----------
    cenario = CENARIOS[numero % len(CENARIOS)]
    plano = planos[1] if demo else planos[numero % len(planos)]
    meses = plano.duracao_meses
    if demo:
        inicio = hoje - timedelta(days=48)
    elif cenario == "vencendo":           # termina daqui a 1 a 6 dias
        inicio = somar_meses(hoje + timedelta(days=rnd.randint(1, 6)), -meses) + timedelta(days=1)
    elif cenario == "vencida":            # terminou entre 4 e 40 dias atrás
        inicio = somar_meses(hoje - timedelta(days=rnd.randint(4, 40)), -meses) + timedelta(days=1)
    else:                                 # começou há poucos dias, ainda vale
        inicio = hoje - timedelta(days=rnd.randint(5, 25))

    matriculas = MatriculaRepositorio(conexao)
    if numero % 2 == 0 and cenario != "cancelada":
        # matrícula antiga (mensal) que terminou um dia antes da atual
        matriculas.salvar(Matricula.nova(aluno.id, planos[0], somar_meses(inicio, -1), "pix"))
    atual = matriculas.salvar(Matricula.nova(aluno.id, plano, inicio, rnd.choice(["pix", "cartao", "dinheiro"])))
    if cenario == "renovada":             # já pagou o próximo período
        matriculas.salvar(Matricula.nova(aluno.id, plano, atual.data_fim + timedelta(days=1), "pix"))
    if cenario == "cancelada":
        atual.cancelar()
        matriculas.salvar(atual)

    # ---------- 3. check-ins dos últimos 60 dias ----------
    assiduidade = 0.72 if demo else rnd.uniform(0.25, 0.85)   # chance de ir treinar em cada dia
    validas = [m for m in matriculas.listar_do_aluno(aluno.id) if m.status == "ativa"]
    checkins = CheckinRepositorio(conexao)
    dias_que_treinou = []
    for dias_atras in range(60, -1, -1):
        dia = hoje - timedelta(days=dias_atras)
        horario = academia.horario_do_dia(dia.weekday())
        tem_plano = any(m.vale_em(dia) for m in validas)
        if horario is None or not tem_plano or rnd.random() > assiduidade:
            continue
        hora = rnd.choice(HORAS_CHECKIN)
        if not horario.abertura.hour <= hora < horario.fechamento.hour:
            hora = horario.abertura.hour + 1                     # ajusta para dentro do horário do dia
        momento = datetime.combine(dia, time(hora, rnd.choice([0, 15, 30, 45])))
        if dia == hoje and (demo or momento > agora):
            continue                                             # não cria check-in no futuro
        checkins.salvar(Checkin(aluno_id=aluno.id, data=dia, hora=momento.time()))
        dias_que_treinou.append(dia)

    # ---------- 4. fichas de treino (A, B, C) e treinos realizados ----------
    if not aluno.personal_id or cenario in ("vencida", "cancelada"):
        return
    fator = rnd.uniform(0.7, 1.4)        # alunos mais fortes ou mais fracos (multiplica a carga)
    fichas = []
    for letra in ("A", "B", "C"):
        nome_treino, lista = FICHAS[letra]
        if aluno.objetivo in ("Emagrecimento", "Condicionamento físico"):
            lista = lista + [CARDIO_FINAL]
        treino = Treino(aluno_id=aluno.id, personal_id=aluno.personal_id, nome=nome_treino,
                        observacoes="Aquecer 5 min antes. Aumente a carga quando completar todas as "
                                    "repetições com facilidade.")
        itens = []
        for exercicio, series, reps, carga, descanso in lista:
            carga_aluno = round(carga * fator / 2.5) * 2.5 if carga else None   # arredonda de 2,5 em 2,5 kg
            itens.append(ItemTreino(exercicio_id=exercicios[exercicio], series=series, repeticoes=reps,
                                    carga_kg=carga_aluno, descanso_seg=descanso))
        treino.definir_itens(itens)
        fichas.append(TreinoRepositorio(conexao).salvar(treino))

    # em cada dia de check-in o aluno fez a próxima ficha da sequência A -> B -> C
    realizados = TreinoRealizadoRepositorio(conexao)
    for vez, dia in enumerate(dias_que_treinou):
        ficha = fichas[vez % 3]
        total = ficha.total_series
        feitas = total if rnd.random() < 0.8 else total - rnd.randint(1, 4)
        realizados.salvar(TreinoRealizado(aluno_id=aluno.id, treino_id=ficha.id, data=dia, series_feitas=feitas,
                                          series_total=total, duracao_min=rnd.randint(42, 78)))
