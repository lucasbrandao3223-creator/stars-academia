"""Regras de matrícula: assinar, renovar, matricular na recepção e cancelar."""
from datetime import datetime, timedelta

import config
from exceptions import MatriculaErro, NaoEncontradoErro, PermissaoNegadaErro
from matricula import Matricula
from usuario import Aluno
from matricula_repo import MatriculaRepositorio
from plano_repo import PlanoRepositorio
from usuario_repo import UsuarioRepositorio
from utils import formatar_data, para_data


class MatriculaService:

    def __init__(self, conexao, relogio=datetime.now):
        self._agora = relogio      # injetado para os testes simularem qualquer data
        self.matriculas = MatriculaRepositorio(conexao)
        self.planos = PlanoRepositorio(conexao)
        self.usuarios = UsuarioRepositorio(conexao)

    def hoje(self):
        return self._agora().date()

    def planos_com_economia(self):
        """Planos ativos com o % de economia em relação ao plano mensal."""
        planos = self.planos.listar()
        referencia = max((p.preco_mensal for p in planos), default=0)
        for p in planos:
            p.economia = p.economia_sobre(referencia)
        return planos

    def situacao_do_aluno(self, aluno_id):
        hoje = self.hoje()
        vigente = self.matriculas.vigente_do_aluno(aluno_id, hoje)
        agendada = self.matriculas.agendada_do_aluno(aluno_id, hoje)
        historico = self.matriculas.listar_do_aluno(aluno_id)
        return {
            "vigente": vigente,
            "agendada": agendada,
            "historico": historico,
            "pode_contratar": agendada is None and (vigente is None
                                                    or vigente.pode_renovar(hoje, config.DIAS_PARA_RENOVAR)),
        }

    def _inicio_da_proxima(self, aluno_id, respeitar_janela=True):
        """Quando começaria uma nova matrícula: hoje, ou no dia seguinte ao fim da atual (renovação)."""
        hoje = self.hoje()
        if self.matriculas.agendada_do_aluno(aluno_id, hoje):
            raise MatriculaErro("Já existe uma renovação agendada para este aluno.")
        vigente = self.matriculas.vigente_do_aluno(aluno_id, hoje)
        if vigente is None:
            return hoje
        if respeitar_janela and not vigente.pode_renovar(hoje, config.DIAS_PARA_RENOVAR):
            raise MatriculaErro(f"Seu plano está ativo até {formatar_data(vigente.data_fim)}. A renovação fica "
                                f"liberada nos últimos {config.DIAS_PARA_RENOVAR} dias.")
        return vigente.data_fim + timedelta(days=1)

    def assinar(self, usuario, plano_id, forma_pagamento):
        """O próprio aluno contrata (ou renova) um plano pelo site."""
        if not isinstance(usuario, Aluno):
            raise PermissaoNegadaErro("Somente alunos podem assinar planos pelo site.")
        plano = self.planos.obter(int(plano_id))
        inicio = self._inicio_da_proxima(usuario.id)
        matricula = Matricula.nova(usuario.id, plano, inicio, forma_pagamento)
        self.matriculas.salvar(matricula)
        return self.matriculas.obter(matricula.id)

    def matricular(self, admin, aluno_id, plano_id, forma_pagamento, data_inicio=None):
        """A recepção matricula (ou renova) um aluno."""
        if not admin.eh_admin:
            raise PermissaoNegadaErro("Somente a administração pode matricular alunos.")
        aluno = self.usuarios.obter(int(aluno_id))
        if not isinstance(aluno, Aluno):
            raise NaoEncontradoErro("Aluno não encontrado.")
        plano = self.planos.obter(int(plano_id))
        inicio = para_data(data_inicio) if data_inicio else self._inicio_da_proxima(aluno.id, respeitar_janela=False)
        matricula = Matricula.nova(aluno.id, plano, inicio, forma_pagamento)
        self.matriculas.salvar(matricula)     # o trigger do banco impede períodos sobrepostos
        return self.matriculas.obter(matricula.id)

    def cancelar(self, admin, matricula_id):
        if not admin.eh_admin:
            raise PermissaoNegadaErro("Somente a administração pode cancelar matrículas.")
        matricula = self.matriculas.obter(int(matricula_id))
        matricula.cancelar()
        return self.matriculas.salvar(matricula)
