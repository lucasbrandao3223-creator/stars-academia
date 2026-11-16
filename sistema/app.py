"""STARS Academia - sistema web (Flask).

Executar (da pasta principal):  python sistema/app.py   e abrir  http://127.0.0.1:5000
"""
from datetime import datetime
from functools import wraps

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for

import config
from database import BancoDeDados
from exceptions import AcademiaErro, NaoEncontradoErro, PermissaoNegadaErro
from models.matricula import FormaPagamento, SituacaoMatricula
from models.usuario import Aluno
from repositories import (AcademiaRepositorio, ExercicioRepositorio, GrupoMuscularRepositorio,
                          UsuarioRepositorio)
from services import AuthService, CheckinService, GestaoService, MatriculaService, TreinoService
from utils import DIAS_SEMANA, formatar_data, formatar_moeda, formatar_telefone, hora_str, para_data

# templates e static ficam fora da pasta "sistema" (na pasta principal do projeto)
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["SECRET_KEY"] = config.SECRET_KEY
banco = BancoDeDados()


def garantir_banco():
    """Na primeira execução cria o banco com os dados de exemplo automaticamente."""
    if not banco.existe():
        from init_db import recriar_banco
        recriar_banco(banco.caminho)


garantir_banco()


# ======================================================================
# Infraestrutura
# ======================================================================
def conexao():
    if "db" not in g:
        g.db = banco.conectar()
    return g.db


@app.teardown_appcontext
def fechar_conexao(_erro):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def carregar_usuario():
    g.usuario = None
    usuario_id = session.get("usuario_id")
    if usuario_id:
        g.usuario = UsuarioRepositorio(conexao()).buscar_por_id(usuario_id)
        if g.usuario is None:
            session.clear()


@app.context_processor
def variaveis_globais():
    if "academia" not in g:
        g.academia = AcademiaRepositorio(conexao()).carregar()
    return {"usuario": g.get("usuario"), "academia": g.academia, "agora": datetime.now(),
            "Situacao": SituacaoMatricula, "FormaPagamento": FormaPagamento}


app.add_template_filter(formatar_moeda, "moeda")
app.add_template_filter(formatar_data, "data_br")
app.add_template_filter(formatar_telefone, "telefone")
app.add_template_filter(hora_str, "hora")


@app.template_filter("dia_extenso")
def dia_extenso(data):
    d = para_data(data)
    return f"{DIAS_SEMANA[d.weekday()]}, {d.strftime('%d/%m')}"


@app.template_filter("dias_atras")
def dias_atras(data):
    if not data:
        return "nunca"
    dias = (datetime.now().date() - para_data(data)).days
    return "hoje" if dias == 0 else "ontem" if dias == 1 else f"há {dias} dias"


def login_obrigatorio(funcao):
    @wraps(funcao)
    def verificar(*args, **kwargs):
        if g.usuario is None:
            flash("Entre na sua conta para continuar.", "info")
            return redirect(url_for("login", proximo=request.full_path))
        return funcao(*args, **kwargs)
    return verificar


def aluno_obrigatorio(funcao):
    @wraps(funcao)
    @login_obrigatorio
    def verificar(*args, **kwargs):
        if not isinstance(g.usuario, Aluno):
            return redirect(url_for(g.usuario.pagina_inicial()))
        return funcao(*args, **kwargs)
    return verificar


def equipe_obrigatoria(funcao):
    @wraps(funcao)
    @login_obrigatorio
    def verificar(*args, **kwargs):
        if not g.usuario.faz_parte_da_equipe:
            flash("Área exclusiva da equipe da academia.", "erro")
            return redirect(url_for("index"))
        return funcao(*args, **kwargs)
    return verificar


def admin_obrigatorio(funcao):
    @wraps(funcao)
    @login_obrigatorio
    def verificar(*args, **kwargs):
        if not g.usuario.eh_admin:
            flash("Área exclusiva da administração.", "erro")
            return redirect(url_for(g.usuario.pagina_inicial()))
        return funcao(*args, **kwargs)
    return verificar


def voltar(padrao="index", **kwargs):
    return redirect(request.referrer or url_for(padrao, **kwargs))


def _destino_seguro(proximo):
    return proximo if proximo and proximo.startswith("/") and not proximo.startswith("//") else None


@app.errorhandler(404)
def nao_encontrado(_erro):
    return render_template("erro.html", titulo="Página não encontrada",
                           mensagem="O endereço que você tentou acessar não existe."), 404


@app.errorhandler(NaoEncontradoErro)
def registro_nao_encontrado(erro):
    return render_template("erro.html", titulo="Não encontrado", mensagem=str(erro)), 404


@app.errorhandler(PermissaoNegadaErro)
def permissao_negada(erro):
    return render_template("erro.html", titulo="Acesso negado", mensagem=str(erro)), 403


# ======================================================================
# Site público
# ======================================================================
@app.route("/")
def index():
    db = conexao()
    hoje = datetime.now().date()
    gestao = GestaoService(db)
    numeros = {
        "alunos": gestao.matriculas.estatisticas(hoje)["alunos_ativos"],
        "exercicios": len(gestao.exercicios.listar()),
        "checkins": gestao.checkins.contar(),
    }
    return render_template("index.html", planos=MatriculaService(db).planos_com_economia(),
                           personais=UsuarioRepositorio(db).listar_personais(), numeros=numeros)


@app.route("/personais")
def personais():
    lista = UsuarioRepositorio(conexao()).listar_personais()
    tags = []
    for p in lista:
        for t in p.tags:
            if t not in tags:
                tags.append(t)
    return render_template("personais.html", personais=lista, tags=tags)


@app.route("/personais/<int:personal_id>/escolher", methods=["POST"])
@aluno_obrigatorio
def escolher_personal(personal_id):
    try:
        p = GestaoService(conexao()).escolher_personal(g.usuario, personal_id)
        flash(f"Agora {p.primeiro_nome} é seu personal! Fale com {p.primeiro_nome} na academia para montar seu treino.",
              "sucesso")
        return redirect(url_for("aluno_painel"))
    except AcademiaErro as erro:
        flash(str(erro), "erro")
        return redirect(url_for("personais"))


@app.route("/entrar", methods=["GET", "POST"])
def login():
    proximo = _destino_seguro(request.values.get("proximo"))
    if request.method == "POST":
        try:
            usuario = AuthService(conexao()).autenticar(request.form.get("email"), request.form.get("senha"))
            session.clear()
            session["usuario_id"] = usuario.id
            flash(f"Bem-vindo(a), {usuario.primeiro_nome}!", "sucesso")
            return redirect(proximo or url_for(usuario.pagina_inicial()))
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    return render_template("login.html", proximo=proximo, email=request.form.get("email", ""))


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    proximo = _destino_seguro(request.values.get("proximo"))
    if request.method == "POST":
        f = request.form
        try:
            aluno = AuthService(conexao()).cadastrar_aluno(
                f.get("nome"), f.get("email"), f.get("telefone"), f.get("senha"), f.get("confirmacao"),
                f.get("data_nascimento"), f.get("objetivo"))
            session.clear()
            session["usuario_id"] = aluno.id
            flash("Conta criada! Agora escolha seu plano para começar a treinar.", "sucesso")
            return redirect(proximo or url_for("index") + "#planos")
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    return render_template("cadastro.html", form=request.form, proximo=proximo, objetivos=Aluno.OBJETIVOS)


@app.route("/sair")
def sair():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))


@app.route("/assinar/<int:plano_id>", methods=["GET", "POST"])
@login_obrigatorio
def assinar(plano_id):
    servico = MatriculaService(conexao())
    plano = servico.planos.obter(plano_id)
    if not isinstance(g.usuario, Aluno):
        flash("A matrícula da equipe é feita pela recepção na ficha do aluno.", "info")
        return redirect(url_for("index") + "#planos")
    if request.method == "POST":
        try:
            m = servico.assinar(g.usuario, plano_id, request.form.get("forma_pagamento"))
            quando = "a partir de hoje" if m.data_inicio == servico.hoje() else f"a partir de {formatar_data(m.data_inicio)}"
            flash(f"Plano {m.plano_nome} contratado {quando}. Bons treinos!", "sucesso")
            return redirect(url_for("aluno_painel"))
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    situacao = servico.situacao_do_aluno(g.usuario.id)
    return render_template("assinar.html", plano=plano, situacao=situacao, hoje=servico.hoje())


# ======================================================================
# Área do aluno
# ======================================================================
@app.route("/aluno")
@aluno_obrigatorio
def aluno_painel():
    db = conexao()
    treinos = TreinoService(db).painel_do_aluno(g.usuario)
    return render_template("aluno/painel.html",
                           matricula=MatriculaService(db).situacao_do_aluno(g.usuario.id),
                           checkin=CheckinService(db).situacao_hoje(g.usuario),
                           frequencia=CheckinService(db).frequencia(g.usuario.id, meta_semanal=g.usuario.meta_semanal),
                           hoje=datetime.now().date(), dias_renovar=config.DIAS_PARA_RENOVAR, **treinos)


@app.route("/aluno/frequencia")
@aluno_obrigatorio
def aluno_frequencia():
    """JSON do calendário de um mês (o JavaScript troca de mês sem recarregar a página)."""
    try:
        dados = CheckinService(conexao()).frequencia(g.usuario.id, request.args.get("ano", type=int),
                                                     request.args.get("mes", type=int), g.usuario.meta_semanal)
        return jsonify(dados)
    except ValueError:
        return jsonify({"erro": "Mês inválido."}), 400


@app.route("/aluno/meta", methods=["POST"])
@aluno_obrigatorio
def aluno_meta():
    dados = request.get_json(silent=True) or request.form
    try:
        aluno = GestaoService(conexao()).definir_meta(g.usuario, dados.get("meta"))
        return jsonify({"ok": True, "meta": aluno.meta_semanal})
    except AcademiaErro as erro:
        return jsonify({"ok": False, "erro": str(erro)}), 400


@app.route("/aluno/treinos/<int:treino_id>/concluir", methods=["POST"])
@aluno_obrigatorio
def aluno_concluir_treino(treino_id):
    dados = request.get_json(silent=True) or request.form
    try:
        realizado, checkin_auto = TreinoService(conexao()).concluir_treino(
            g.usuario, treino_id, dados.get("series_feitas"), dados.get("duracao_min"))
        msg = f"Treino concluído! {realizado.series_feitas}/{realizado.series_total} séries em {realizado.duracao_min} min."
        if checkin_auto:
            msg += " Check-in de hoje registrado automaticamente."
        flash(msg + " Você é uma estrela! ⭐", "sucesso")
        return jsonify({"ok": True, "mensagem": msg})
    except AcademiaErro as erro:
        return jsonify({"ok": False, "erro": str(erro)}), 400


@app.route("/aluno/checkin", methods=["POST"])
@aluno_obrigatorio
def aluno_checkin():
    try:
        c = CheckinService(conexao()).fazer_checkin(g.usuario)
        flash(f"Check-in feito às {c.hora_texto}. Bora brilhar! ⭐", "sucesso")
    except AcademiaErro as erro:
        flash(str(erro), "erro")
    return redirect(url_for("aluno_painel"))


# ======================================================================
# Área da equipe (personal e administrador)
# ======================================================================
@app.route("/equipe/alunos")
@equipe_obrigatoria
def equipe_alunos():
    filtro = {"busca": request.args.get("busca", "").strip(),
              "meus": request.args.get("meus") == "1",
              "situacao": request.args.get("situacao", "")}
    alunos = GestaoService(conexao()).alunos(g.usuario, filtro["busca"], filtro["meus"], filtro["situacao"])
    return render_template("equipe/alunos.html", alunos=alunos, filtro=filtro, hoje=datetime.now().date())


@app.route("/equipe/alunos/<int:aluno_id>")
@equipe_obrigatoria
def equipe_ficha(aluno_id):
    db = conexao()
    gestao = GestaoService(db)
    aluno = gestao.obter_aluno(g.usuario, aluno_id)
    matriculas = MatriculaService(db)
    return render_template("equipe/ficha.html", aluno=aluno,
                           matricula=matriculas.situacao_do_aluno(aluno.id),
                           planos=matriculas.planos.listar(),
                           frequencia=CheckinService(db).frequencia(aluno.id),
                           ultimos_checkins=gestao.checkins.ultimos_do_aluno(aluno.id, 8),
                           treinos=TreinoService(db).treinos_do_aluno(g.usuario, aluno.id, apenas_ativos=False),
                           personais=gestao.usuarios.listar_personais(),
                           hoje=datetime.now().date())


@app.route("/equipe/alunos/<int:aluno_id>/personal", methods=["POST"])
@equipe_obrigatoria
def equipe_definir_personal(aluno_id):
    try:
        aluno = GestaoService(conexao()).definir_personal(g.usuario, aluno_id, request.form.get("personal_id"))
        flash(f"Personal de {aluno.primeiro_nome} atualizado.", "sucesso")
    except AcademiaErro as erro:
        flash(str(erro), "erro")
    return redirect(url_for("equipe_ficha", aluno_id=aluno_id))


def _linhas_do_formulario(form):
    """O formulário de treino manda uma lista para cada coluna (exercicio_id, series...).

    Aqui juntamos essas listas em uma lista de dicionários, um por exercício. Ex.:
    exercicio_id=[1, 5] e series=[4, 3]  ->  [{"exercicio_id": 1, "series": 4}, {"exercicio_id": 5, "series": 3}]
    """
    exercicios = form.getlist("exercicio_id")
    series = form.getlist("series")
    repeticoes = form.getlist("repeticoes")
    cargas = form.getlist("carga_kg")
    descansos = form.getlist("descanso_seg")
    observacoes = form.getlist("observacao")

    linhas = []
    for i in range(len(exercicios)):
        linhas.append({
            "exercicio_id": exercicios[i],
            "series": series[i],
            "repeticoes": repeticoes[i],
            "carga_kg": cargas[i],
            "descanso_seg": descansos[i],
            "observacao": observacoes[i],
        })
    return linhas


@app.route("/equipe/alunos/<int:aluno_id>/treinos/novo", methods=["GET", "POST"])
@app.route("/equipe/alunos/<int:aluno_id>/treinos/<int:treino_id>", methods=["GET", "POST"])
@equipe_obrigatoria
def equipe_treino(aluno_id, treino_id=None):
    db = conexao()
    servico = TreinoService(db)
    aluno = GestaoService(db).obter_aluno(g.usuario, aluno_id)
    if not g.usuario.pode_montar_treino():
        flash("Somente personal trainers montam treinos. Você pode visualizar na ficha do aluno.", "info")
        return redirect(url_for("equipe_ficha", aluno_id=aluno_id))
    linhas = None
    if request.method == "POST":
        linhas = _linhas_do_formulario(request.form)
        try:
            t = servico.salvar_treino(g.usuario, aluno.id, request.form.get("nome"),
                                      request.form.get("observacoes"), linhas, treino_id)
            flash(f"\"{t.nome}\" salvo para {aluno.primeiro_nome}.", "sucesso")
            return redirect(url_for("equipe_ficha", aluno_id=aluno.id) + "#treinos")
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    treino = servico.treinos.obter(treino_id) if treino_id else None
    if treino and treino.aluno_id != aluno.id:
        raise NaoEncontradoErro("Treino não encontrado para este aluno.")
    if linhas is None:
        linhas = ([{"exercicio_id": i.exercicio_id, "series": i.series, "repeticoes": i.repeticoes,
                    "carga_kg": "" if i.carga_kg is None else i.carga_kg, "descanso_seg": i.descanso_seg,
                    "observacao": i.observacao} for i in treino.itens] if treino else [])
    sugestoes = ["Treino A - Peito, Ombros e Tríceps", "Treino B - Costas e Bíceps", "Treino C - Pernas e Glúteos",
                 "Treino D - Full body", "Treino Cardio e Abdômen"]
    return render_template("equipe/treino_form.html", aluno=aluno, treino=treino, linhas=linhas,
                           form=request.form, sugestoes=sugestoes,
                           exercicios=ExercicioRepositorio(db).listar())


@app.route("/equipe/treinos/<int:treino_id>/alternar", methods=["POST"])
@equipe_obrigatoria
def equipe_alternar_treino(treino_id):
    try:
        t = TreinoService(conexao()).alternar_treino(g.usuario, treino_id)
        flash(f"\"{t.nome}\" {'reativado' if t.ativo else 'arquivado (o aluno não vê mais)'}.", "info")
    except AcademiaErro as erro:
        flash(str(erro), "erro")
    return voltar("equipe_alunos")


@app.route("/equipe/exercicios", methods=["GET", "POST"])
@app.route("/equipe/exercicios/<int:exercicio_id>", methods=["GET", "POST"])
@equipe_obrigatoria
def equipe_exercicios(exercicio_id=None):
    db = conexao()
    gestao = GestaoService(db)
    if request.method == "POST":
        try:
            ex = gestao.salvar_exercicio(g.usuario, request.form, exercicio_id)
            flash(f"Exercício \"{ex.nome}\" salvo.", "sucesso")
            return redirect(url_for("equipe_exercicios"))
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    grupo = request.args.get("grupo", type=int)
    return render_template("equipe/exercicios.html", form=request.form, grupo_atual=grupo,
                           editando=gestao.exercicios.obter(exercicio_id) if exercicio_id else None,
                           grupos=GrupoMuscularRepositorio(db).listar_todos(),
                           exercicios=gestao.exercicios.listar(grupo))


@app.route("/equipe/exercicios/<int:exercicio_id>/excluir", methods=["POST"])
@equipe_obrigatoria
def equipe_excluir_exercicio(exercicio_id):
    try:
        ex = GestaoService(conexao()).excluir_exercicio(g.usuario, exercicio_id)
        flash(f"\"{ex.nome}\" excluído.", "info")
    except AcademiaErro as erro:
        flash(str(erro), "erro")
    return redirect(url_for("equipe_exercicios"))


# ======================================================================
# Administração
# ======================================================================
@app.route("/admin")
@admin_obrigatorio
def admin_dashboard():
    dados = GestaoService(conexao()).painel(g.usuario)
    maiores = {
        "dia": max([d["total"] for d in dados["por_dia"]] + [1]),
        "hora": max([h["total"] for h in dados["por_hora"]] + [1]),
        "fat": max([f["faturamento"] for f in dados["faturamento"]] + [1]),
        "plano": max([p["total"] for p in dados["planos"]] + [1]),
    }
    return render_template("admin/dashboard.html", maiores=maiores, hoje=datetime.now().date(), **dados)


@app.route("/admin/matriculas")
@admin_obrigatorio
def admin_matriculas():
    filtro = {"situacao": request.args.get("situacao", "ativa"), "busca": request.args.get("busca", "").strip()}
    servico = MatriculaService(conexao())
    lista = servico.matriculas.listar(servico.hoje(), filtro["situacao"] or None, filtro["busca"],
                                      config.DIAS_ALERTA_VENCIMENTO)
    return render_template("admin/matriculas.html", matriculas=lista, filtro=filtro, hoje=servico.hoje())


@app.route("/admin/alunos/<int:aluno_id>/matricular", methods=["POST"])
@admin_obrigatorio
def admin_matricular(aluno_id):
    f = request.form
    try:
        m = MatriculaService(conexao()).matricular(g.usuario, aluno_id, f.get("plano_id"),
                                                   f.get("forma_pagamento"), f.get("data_inicio") or None)
        flash(f"Matrícula no plano {m.plano_nome} registrada ({formatar_data(m.data_inicio)} a "
              f"{formatar_data(m.data_fim)}).", "sucesso")
    except (AcademiaErro, ValueError) as erro:
        flash(str(erro) if isinstance(erro, AcademiaErro) else "Data de início inválida.", "erro")
    return redirect(url_for("equipe_ficha", aluno_id=aluno_id) + "#matricula")


@app.route("/admin/matriculas/<int:matricula_id>/cancelar", methods=["POST"])
@admin_obrigatorio
def admin_cancelar_matricula(matricula_id):
    try:
        m = MatriculaService(conexao()).cancelar(g.usuario, matricula_id)
        flash(f"Matrícula de {m.aluno_nome} cancelada.", "info")
    except AcademiaErro as erro:
        flash(str(erro), "erro")
    return voltar("admin_matriculas")


@app.route("/admin/planos", methods=["GET", "POST"])
@app.route("/admin/planos/<int:plano_id>", methods=["GET", "POST"])
@admin_obrigatorio
def admin_planos(plano_id=None):
    gestao = GestaoService(conexao())
    if request.method == "POST":
        try:
            p = gestao.salvar_plano(g.usuario, request.form, plano_id)
            flash(f"Plano \"{p.nome}\" salvo.", "sucesso")
            return redirect(url_for("admin_planos"))
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    return render_template("admin/planos.html", form=request.form,
                           editando=gestao.planos.obter(plano_id) if plano_id else None,
                           planos=gestao.planos.listar(apenas_ativos=False))


@app.route("/admin/planos/<int:plano_id>/alternar", methods=["POST"])
@admin_obrigatorio
def admin_alternar_plano(plano_id):
    p = GestaoService(conexao()).alternar_plano(g.usuario, plano_id)
    flash(f"Plano \"{p.nome}\" {'ativado' if p.ativo else 'desativado (não aparece mais no site)'}.", "info")
    return redirect(url_for("admin_planos"))


@app.route("/admin/personais", methods=["GET", "POST"])
@app.route("/admin/personais/<int:personal_id>", methods=["GET", "POST"])
@admin_obrigatorio
def admin_personais(personal_id=None):
    gestao = GestaoService(conexao())
    if request.method == "POST":
        try:
            p = gestao.salvar_personal(g.usuario, request.form, personal_id)
            flash(f"{p.nome} salvo(a) na equipe.", "sucesso")
            return redirect(url_for("admin_personais"))
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    editando = gestao.usuarios.obter(personal_id) if personal_id else None
    return render_template("admin/personais.html", form=request.form, editando=editando,
                           personais=gestao.usuarios.listar_personais(apenas_ativos=False))


@app.route("/admin/personais/<int:personal_id>/alternar", methods=["POST"])
@admin_obrigatorio
def admin_alternar_personal(personal_id):
    p = GestaoService(conexao()).alternar_personal(g.usuario, personal_id)
    flash(f"{p.nome} {'reativado(a)' if p.ativo else 'desativado(a)'}.", "info")
    return redirect(url_for("admin_personais"))


@app.route("/admin/academia", methods=["GET", "POST"])
@admin_obrigatorio
def admin_academia():
    if request.method == "POST":
        f = request.form
        horarios = [(d, f.get(f"abertura_{d}"), f.get(f"fechamento_{d}")) for d in range(7) if f.get(f"aberto_{d}")]
        try:
            GestaoService(conexao()).atualizar_academia(g.usuario, f, horarios)
            g.pop("academia", None)
            flash("Dados da academia atualizados.", "sucesso")
            return redirect(url_for("admin_academia"))
        except AcademiaErro as erro:
            flash(str(erro), "erro")
    return render_template("admin/academia.html", dias=DIAS_SEMANA)


if __name__ == "__main__":
    app.run(debug=True)
