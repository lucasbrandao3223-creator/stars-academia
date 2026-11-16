"""Matrícula do aluno em um plano, e o check-in na academia."""
from datetime import date, timedelta
from enum import Enum

from exceptions import MatriculaErro, ValidacaoErro
from entidade import Entidade
from utils import formatar_moeda, formatar_telefone, hora_str, para_data, para_hora, somar_meses


class SituacaoMatricula(str, Enum):
    ATIVA = "ativa"
    AGENDADA = "agendada"     # renovação paga que começa depois da atual
    VENCIDA = "vencida"
    CANCELADA = "cancelada"

    @property
    def rotulo(self):
        return {"ativa": "Ativa", "agendada": "Agendada", "vencida": "Vencida",
                "cancelada": "Cancelada"}[self.value]


class FormaPagamento(str, Enum):
    PIX = "pix"
    CARTAO = "cartao"
    DINHEIRO = "dinheiro"

    @property
    def rotulo(self):
        return {"pix": "Pix", "cartao": "Cartão", "dinheiro": "Dinheiro"}[self.value]


class Matricula(Entidade):
    """Período em que o aluno pode treinar. 'Vencida' não é gravada: é calculada pela data."""

    def __init__(self, aluno_id, plano_id, data_inicio, data_fim, valor_total, forma_pagamento,
                 status="ativa", id=None, criado_em=None, aluno_nome=None, aluno_telefone=None,
                 plano_nome=None):
        super().__init__(id)
        self.aluno_id = aluno_id
        self.plano_id = plano_id
        self.data_inicio = para_data(data_inicio)
        self.data_fim = para_data(data_fim)
        self.valor_total = float(valor_total)
        try:
            self.forma_pagamento = FormaPagamento(forma_pagamento)
        except ValueError:
            raise ValidacaoErro("Escolha a forma de pagamento.")
        if status not in ("ativa", "cancelada"):
            raise ValidacaoErro("Status de matrícula inválido.")
        self._cancelada = status == "cancelada"
        self.criado_em = criado_em
        self.aluno_nome = aluno_nome
        self.aluno_telefone = aluno_telefone
        self.plano_nome = plano_nome

    @classmethod
    def nova(cls, aluno_id, plano, data_inicio, forma_pagamento):
        """Cria a matrícula calculando o fim do período e o valor a partir do plano."""
        if not plano.ativo:
            raise MatriculaErro("Esse plano não está mais disponível.")
        inicio = para_data(data_inicio)
        fim = somar_meses(inicio, plano.duracao_meses) - timedelta(days=1)
        return cls(aluno_id=aluno_id, plano_id=plano.id, data_inicio=inicio, data_fim=fim,
                   valor_total=plano.valor_total, forma_pagamento=forma_pagamento, plano_nome=plano.nome)

    # ---------------- estado ----------------
    @property
    def status(self):
        return "cancelada" if self._cancelada else "ativa"

    def situacao(self, hoje=None):
        hoje = hoje or date.today()
        if self._cancelada:
            return SituacaoMatricula.CANCELADA
        if hoje > self.data_fim:
            return SituacaoMatricula.VENCIDA
        if hoje < self.data_inicio:
            return SituacaoMatricula.AGENDADA
        return SituacaoMatricula.ATIVA

    def cancelar(self):
        if self._cancelada:
            raise MatriculaErro("Essa matrícula já está cancelada.")
        self._cancelada = True

    def vale_em(self, data):
        """True se o aluno pode treinar nessa data com esta matrícula."""
        data = para_data(data)
        return not self._cancelada and self.data_inicio <= data <= self.data_fim

    def dias_restantes(self, hoje=None):
        return (self.data_fim - (hoje or date.today())).days

    def progresso(self, hoje=None):
        """Percentual do período já utilizado (0 a 100)."""
        hoje = hoje or date.today()
        total = (self.data_fim - self.data_inicio).days + 1
        usados = min(max((hoje - self.data_inicio).days + 1, 0), total)
        return round(100 * usados / total)

    def pode_renovar(self, hoje=None, dias_antes=15):
        return self.situacao(hoje) == SituacaoMatricula.ATIVA and self.dias_restantes(hoje) <= dias_antes

    @property
    def valor_formatado(self):
        return formatar_moeda(self.valor_total)

    @property
    def aluno_telefone_formatado(self):
        return formatar_telefone(self.aluno_telefone)

    def validar(self):
        if self.data_inicio > self.data_fim:
            raise ValidacaoErro("A data de início deve ser antes do fim.")


class Checkin(Entidade):
    """Entrada do aluno na academia (uma por dia)."""

    def __init__(self, aluno_id, data, hora, id=None, aluno_nome=None):
        super().__init__(id)
        self.aluno_id = aluno_id
        self.data = para_data(data)
        self.hora = para_hora(hora)
        self.aluno_nome = aluno_nome

    @property
    def hora_texto(self):
        return hora_str(self.hora)

    def validar(self):
        if not self.aluno_id:
            raise ValidacaoErro("Check-in sem aluno.")
