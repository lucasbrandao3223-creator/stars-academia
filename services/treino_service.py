"""Montagem de treinos pelo personal e execução do treino pelo aluno."""
from datetime import datetime, timedelta

from exceptions import NaoEncontradoErro, PermissaoNegadaErro, ValidacaoErro
from models.matricula import Checkin
from models.treino import ItemTreino, Treino, TreinoRealizado
from models.usuario import Aluno
from repositories import (AcademiaRepositorio, CheckinRepositorio, ExercicioRepositorio, MatriculaRepositorio,
                          TreinoRealizadoRepositorio, TreinoRepositorio, UsuarioRepositorio)


class TreinoService:

    def __init__(self, conexao, relogio=datetime.now):
        self._agora = relogio
        self.treinos = TreinoRepositorio(conexao)
        self.exercicios = ExercicioRepositorio(conexao)
        self.usuarios = UsuarioRepositorio(conexao)
        self.realizados = TreinoRealizadoRepositorio(conexao)
        self.matriculas = MatriculaRepositorio(conexao)
        self.checkins = CheckinRepositorio(conexao)
        self.academia = AcademiaRepositorio(conexao)

    def treinos_do_aluno(self, usuario, aluno_id, apenas_ativos=True):
        # polimorfismo: o Aluno só vê os próprios; Personal e Administrador veem todos
        if not usuario.pode_ver_aluno(aluno_id):
            raise PermissaoNegadaErro("Você não pode ver os treinos deste aluno.")
        return self.treinos.listar_do_aluno(aluno_id, apenas_ativos)

    def salvar_treino(self, usuario, aluno_id, nome, observacoes, linhas, treino_id=None):
        """linhas: lista de dicts com exercicio_id, series, repeticoes, carga_kg, descanso_seg, observacao."""
        if not usuario.pode_montar_treino():
            raise PermissaoNegadaErro("Somente personal trainers ativos podem montar treinos.")
        aluno = self.usuarios.obter(int(aluno_id))
        if not isinstance(aluno, Aluno):
            raise NaoEncontradoErro("Aluno não encontrado.")

        validos = {e.id for e in self.exercicios.listar()}
        itens = []
        for linha in linhas:
            if not str(linha.get("exercicio_id") or "").strip():
                continue          # linha em branco no formulário
            item = ItemTreino(**linha)
            if item.exercicio_id not in validos:
                raise ValidacaoErro("Exercício inválido no treino.")
            itens.append(item)

        if treino_id:
            treino = self.treinos.obter(int(treino_id))
            if treino.aluno_id != aluno.id:
                raise PermissaoNegadaErro("Esse treino é de outro aluno.")
            treino.nome = nome
            treino.observacoes = (observacoes or "").strip()
            treino.personal_id = usuario.id      # quem editou por último passa a ser o responsável
        else:
            treino = Treino(aluno_id=aluno.id, personal_id=usuario.id, nome=nome, observacoes=observacoes)
        treino.definir_itens(itens)
        return self.treinos.salvar(treino)

    def alternar_treino(self, usuario, treino_id):
        if not usuario.pode_montar_treino():
            raise PermissaoNegadaErro("Somente personal trainers podem arquivar treinos.")
        treino = self.treinos.obter(int(treino_id))
        treino.ativo = not treino.ativo
        return self.treinos.alterar_ativo(treino)

    # ------------------------------------------------------------------
    # Execução do treino pelo aluno
    # ------------------------------------------------------------------
    def painel_do_aluno(self, aluno):
        """Treinos ativos com o último dia realizado, se já foi feito hoje e qual é o próximo sugerido."""
        hoje = self._agora().date()
        treinos = self.treinos_do_aluno(aluno, aluno.id)
        ultimos = self.realizados.ultimo_por_treino(aluno.id)
        for t in treinos:
            t.ultima_vez = ultimos.get(t.id)
            t.feito_hoje = t.ultima_vez == hoje
        proximo = None
        if treinos:
            # sugere o treino feito há mais tempo (ou nunca feito), seguindo a ordem A, B, C...
            proximo = min(treinos, key=lambda t: (t.ultima_vez or hoje - timedelta(days=9999), t.nome))
        return {"treinos": treinos, "proximo": proximo,
                "historico": self.realizados.ultimos_do_aluno(aluno.id, 8),
                "totais": self.realizados.totais_do_aluno(aluno.id)}

    def concluir_treino(self, usuario, treino_id, series_feitas, duracao_min):
        """O aluno finaliza o treino do dia. Se ainda não fez check-in e a academia está aberta, faz junto."""
        if not isinstance(usuario, Aluno):
            raise PermissaoNegadaErro("Somente o aluno pode concluir o próprio treino.")
        agora = self._agora()
        treino = self.treinos.obter(int(treino_id))
        if treino.aluno_id != usuario.id or not treino.ativo:
            raise PermissaoNegadaErro("Esse treino não está na sua ficha.")
        if self.matriculas.vigente_do_aluno(usuario.id, agora.date()) is None:
            raise ValidacaoErro("Você precisa de um plano ativo para registrar treinos.")
        if self.realizados.do_treino_no_dia(treino.id, agora.date()):
            raise ValidacaoErro("Você já concluiu esse treino hoje. Descanse e volte amanhã!")
        try:
            duracao = max(1, min(300, int(float(duracao_min or 1))))
        except (TypeError, ValueError):
            duracao = 1
        realizado = TreinoRealizado(aluno_id=usuario.id, treino_id=treino.id, data=agora.date(),
                                    series_feitas=series_feitas, series_total=treino.total_series,
                                    duracao_min=duracao, treino_nome=treino.nome)
        self.realizados.salvar(realizado)

        checkin_automatico = False
        if (self.checkins.do_aluno_no_dia(usuario.id, agora.date()) is None
                and self.academia.obter().esta_aberta(agora)):
            self.checkins.salvar(Checkin(aluno_id=usuario.id, data=agora.date(), hora=agora.time()))
            checkin_automatico = True
        return realizado, checkin_automatico
