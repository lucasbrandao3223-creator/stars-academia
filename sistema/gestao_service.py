"""Gestão da academia: painel, alunos, planos, personais, exercícios e dados gerais."""
from datetime import datetime

import config
from exceptions import NaoEncontradoErro, PermissaoNegadaErro, ValidacaoErro
from academia import HorarioFuncionamento
from plano import Plano
from treino import Exercicio
from usuario import Aluno, Personal
from academia_repo import AcademiaRepositorio
from matricula_repo import CheckinRepositorio, MatriculaRepositorio
from plano_repo import PlanoRepositorio
from treino_repo import ExercicioRepositorio, GrupoMuscularRepositorio, TreinoRepositorio
from usuario_repo import UsuarioRepositorio
from utils import apenas_digitos


class GestaoService:

    def __init__(self, conexao, relogio=datetime.now):
        self._agora = relogio
        self.academia = AcademiaRepositorio(conexao)
        self.usuarios = UsuarioRepositorio(conexao)
        self.planos = PlanoRepositorio(conexao)
        self.matriculas = MatriculaRepositorio(conexao)
        self.checkins = CheckinRepositorio(conexao)
        self.treinos = TreinoRepositorio(conexao)
        self.grupos = GrupoMuscularRepositorio(conexao)
        self.exercicios = ExercicioRepositorio(conexao)

    # ---------------- permissões ----------------
    @staticmethod
    def exigir_admin(usuario):
        if not usuario or not usuario.eh_admin:
            raise PermissaoNegadaErro("Área exclusiva da administração.")

    @staticmethod
    def exigir_equipe(usuario):
        if not usuario or not usuario.faz_parte_da_equipe:
            raise PermissaoNegadaErro("Área exclusiva da equipe da academia.")

    # ---------------- painel do administrador ----------------
    def painel(self, admin):
        self.exigir_admin(admin)
        hoje = self._agora().date()
        stats = self.matriculas.estatisticas(hoje, config.DIAS_ALERTA_VENCIMENTO)
        checkins_hoje = self.checkins.do_dia(hoje)
        stats["checkins_hoje"] = len(checkins_hoje)
        stats["ticket_medio"] = stats["faturamento_mes"] / stats["matriculas_mes"] if stats["matriculas_mes"] else 0
        return {
            "stats": stats,
            "checkins_hoje": checkins_hoje[:10],
            "por_dia": self.checkins.por_dia(hoje, 14),
            "por_hora": self.checkins.por_hora(hoje, 30),
            "vencendo": self.matriculas.listar(hoje, "vencendo", dias_alerta=config.DIAS_ALERTA_VENCIMENTO)[:8],
            "faturamento": self.matriculas.faturamento_mensal(hoje, 6),
            "planos": self.planos.alunos_por_plano(hoje),
        }

    # ---------------- alunos ----------------
    def alunos(self, usuario, busca=None, somente_meus=False, situacao=None):
        self.exigir_equipe(usuario)
        hoje = self._agora().date()
        personal_id = usuario.id if somente_meus and isinstance(usuario, Personal) else None
        lista = self.usuarios.listar_alunos(busca, personal_id)
        vigentes = {m.aluno_id: m for m in self.matriculas.vigentes(hoje)}
        frequencia = self.checkins.frequencia_alunos(hoje)
        treinos = self.treinos.contar_ativos_por_aluno()
        resultado = []
        for aluno in lista:
            aluno.matricula = vigentes.get(aluno.id)
            freq = frequencia.get(aluno.id, {})
            aluno.ultimo_checkin = freq.get("ultimo")
            aluno.checkins_30 = freq.get("ultimos_30", 0)
            aluno.treinos_ativos = treinos.get(aluno.id, 0)
            if situacao == "ativos" and not aluno.matricula:
                continue
            if situacao == "sem_plano" and aluno.matricula:
                continue
            if situacao == "sem_treino" and (aluno.treinos_ativos or not aluno.matricula):
                continue
            resultado.append(aluno)
        return resultado

    def obter_aluno(self, usuario, aluno_id):
        if not usuario.pode_ver_aluno(aluno_id):
            raise PermissaoNegadaErro("Você não pode ver a ficha deste aluno.")
        aluno = self.usuarios.obter(int(aluno_id))
        if not isinstance(aluno, Aluno):
            raise NaoEncontradoErro("Aluno não encontrado.")
        return aluno

    def definir_personal(self, usuario, aluno_id, personal_id):
        self.exigir_equipe(usuario)
        aluno = self.obter_aluno(usuario, aluno_id)
        if personal_id:
            personal = self.usuarios.obter(int(personal_id))
            if not isinstance(personal, Personal) or not personal.ativo:
                raise ValidacaoErro("Escolha um personal ativo.")
            aluno.personal_id = personal.id
        else:
            aluno.personal_id = None
        return self.usuarios.salvar(aluno)

    def escolher_personal(self, aluno, personal_id):
        """O próprio aluno escolhe com qual personal quer treinar."""
        if not isinstance(aluno, Aluno):
            raise PermissaoNegadaErro("Somente alunos escolhem um personal.")
        personal = self.usuarios.obter(int(personal_id))
        if not isinstance(personal, Personal) or not personal.ativo:
            raise ValidacaoErro("Esse personal não está disponível.")
        aluno.personal_id = personal.id
        self.usuarios.salvar(aluno)
        return personal

    def definir_meta(self, aluno, meta):
        if not isinstance(aluno, Aluno):
            raise PermissaoNegadaErro("Somente alunos têm meta semanal.")
        aluno.meta_semanal = meta
        return self.usuarios.salvar(aluno)

    # ---------------- planos ----------------
    def salvar_plano(self, admin, dados, plano_id=None):
        self.exigir_admin(admin)
        if plano_id:
            plano = self.planos.obter(int(plano_id))
            plano.nome = dados.get("nome")
            plano.descricao = (dados.get("descricao") or "").strip()
            plano.duracao_meses = dados.get("duracao_meses")
            plano.preco_mensal = dados.get("preco_mensal")
        else:
            plano = Plano(nome=dados.get("nome"), descricao=(dados.get("descricao") or "").strip(),
                          duracao_meses=dados.get("duracao_meses"), preco_mensal=dados.get("preco_mensal"))
        return self.planos.salvar(plano)

    def alternar_plano(self, admin, plano_id):
        self.exigir_admin(admin)
        plano = self.planos.obter(int(plano_id))
        plano.desativar() if plano.ativo else plano.ativar()
        return self.planos.salvar(plano)

    # ---------------- personais ----------------
    def salvar_personal(self, admin, dados, personal_id=None):
        self.exigir_admin(admin)
        if personal_id:
            personal = self.usuarios.obter(int(personal_id))
            if not isinstance(personal, Personal):
                raise NaoEncontradoErro("Personal não encontrado.")
            personal.nome = dados.get("nome")
            personal.email = dados.get("email")
            personal.telefone = dados.get("telefone")
            personal.cref = dados.get("cref")
            personal.especialidade = (dados.get("especialidade") or "").strip()
            personal.bio = (dados.get("bio") or "").strip()
            personal.anos_experiencia = dados.get("anos_experiencia")
            if dados.get("senha"):
                personal.definir_senha(dados.get("senha"))
        else:
            personal = Personal(nome=dados.get("nome"), email=dados.get("email"), telefone=dados.get("telefone"),
                                cref=dados.get("cref"), especialidade=dados.get("especialidade"),
                                bio=dados.get("bio"), anos_experiencia=dados.get("anos_experiencia"))
            if self.usuarios.email_existe(personal.email):
                raise ValidacaoErro("Este e-mail já está cadastrado.")
            personal.definir_senha(dados.get("senha"))
        return self.usuarios.salvar(personal)

    def alternar_personal(self, admin, personal_id):
        self.exigir_admin(admin)
        personal = self.usuarios.obter(int(personal_id))
        if not isinstance(personal, Personal):
            raise NaoEncontradoErro("Personal não encontrado.")
        personal.ativo = not personal.ativo
        return self.usuarios.salvar(personal)

    # ---------------- exercícios ----------------
    def salvar_exercicio(self, usuario, dados, exercicio_id=None):
        self.exigir_equipe(usuario)
        grupo = self.grupos.obter(int(dados.get("grupo_muscular_id") or 0))
        if exercicio_id:
            ex = self.exercicios.obter(int(exercicio_id))
            ex.nome = dados.get("nome")
            ex.grupo_muscular_id = grupo.id
            ex.equipamento = (dados.get("equipamento") or "").strip()
            ex.instrucoes = (dados.get("instrucoes") or "").strip()
        else:
            ex = Exercicio(nome=dados.get("nome"), grupo_muscular_id=grupo.id,
                           equipamento=dados.get("equipamento"), instrucoes=dados.get("instrucoes"))
        return self.exercicios.salvar(ex)

    def excluir_exercicio(self, usuario, exercicio_id):
        self.exigir_equipe(usuario)
        ex = self.exercicios.obter(int(exercicio_id))
        if ex.usos:
            raise ValidacaoErro(f"\"{ex.nome}\" está em {ex.usos} treino(s) e não pode ser excluído.")
        self.exercicios.excluir(ex.id)
        return ex

    # ---------------- dados da academia ----------------
    def atualizar_academia(self, admin, dados, horarios):
        self.exigir_admin(admin)
        a = self.academia.obter()
        a.nome = dados.get("nome")
        for campo in ("slogan", "descricao", "endereco", "cidade", "instagram"):
            setattr(a, campo, (dados.get(campo) or "").strip())
        a.telefone = apenas_digitos(dados.get("telefone"))
        a.whatsapp = apenas_digitos(dados.get("whatsapp"))
        novos = []
        for dia, abre, fecha in horarios:
            if not abre or not fecha:
                raise ValidacaoErro("Preencha abertura e fechamento dos dias marcados como abertos.")
            novos.append(HorarioFuncionamento(dia, abre, fecha))
        a.limpar_horarios()
        for h in novos:
            a.definir_horario(h)
        return self.academia.salvar(a)
