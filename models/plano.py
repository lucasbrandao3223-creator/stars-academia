"""Plano de assinatura da academia."""
from exceptions import ValidacaoErro
from models.entidade import Entidade
from utils import formatar_moeda


class Plano(Entidade):

    def __init__(self, nome, duracao_meses, preco_mensal, descricao="", ativo=True, id=None):
        super().__init__(id)
        self.nome = nome
        self.duracao_meses = duracao_meses
        self.preco_mensal = preco_mensal
        self.descricao = descricao or ""
        self.ativo = bool(ativo)

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valor):
        valor = (valor or "").strip()
        if len(valor) < 3:
            raise ValidacaoErro("Informe o nome do plano.")
        self._nome = valor

    @property
    def duracao_meses(self):
        return self._duracao

    @duracao_meses.setter
    def duracao_meses(self, valor):
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            raise ValidacaoErro("Duração inválida.")
        if not 1 <= valor <= 24:
            raise ValidacaoErro("A duração do plano deve ser de 1 a 24 meses.")
        self._duracao = valor

    @property
    def preco_mensal(self):
        return self._preco

    @preco_mensal.setter
    def preco_mensal(self, valor):
        try:
            valor = round(float(str(valor).replace(",", ".")), 2)
        except (TypeError, ValueError):
            raise ValidacaoErro("Preço inválido.")
        if valor <= 0:
            raise ValidacaoErro("O preço mensal deve ser maior que zero.")
        self._preco = valor

    @property
    def valor_total(self):
        return round(self._preco * self._duracao, 2)

    @property
    def preco_formatado(self):
        return formatar_moeda(self._preco)

    @property
    def total_formatado(self):
        return formatar_moeda(self.valor_total)

    @property
    def duracao_texto(self):
        return "1 mês" if self._duracao == 1 else f"{self._duracao} meses"

    def economia_sobre(self, preco_referencia):
        """Percentual de economia em relação a um preço mensal de referência (o plano mensal)."""
        if not preco_referencia or self._preco >= preco_referencia:
            return 0
        return round(100 * (1 - self._preco / preco_referencia))

    def ativar(self):
        self.ativo = True

    def desativar(self):
        self.ativo = False

    def validar(self):
        pass  # as regras já estão nos setters
