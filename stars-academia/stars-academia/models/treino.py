"""Biblioteca de exercícios e fichas de treino."""
from exceptions import ValidacaoErro
from models.entidade import Entidade


class GrupoMuscular(Entidade):

    def __init__(self, nome, id=None):
        super().__init__(id)
        self.nome = (nome or "").strip()

    def validar(self):
        if not self.nome:
            raise ValidacaoErro("Grupo muscular sem nome.")


class Exercicio(Entidade):

    def __init__(self, nome, grupo_muscular_id, equipamento="", instrucoes="", id=None, grupo_nome=None):
        super().__init__(id)
        self.nome = nome
        self.grupo_muscular_id = grupo_muscular_id
        self.equipamento = (equipamento or "").strip()
        self.instrucoes = (instrucoes or "").strip()
        self.grupo_nome = grupo_nome

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valor):
        valor = (valor or "").strip()
        if len(valor) < 3:
            raise ValidacaoErro("Informe o nome do exercício.")
        self._nome = valor

    def validar(self):
        if not self.grupo_muscular_id:
            raise ValidacaoErro("Escolha o grupo muscular do exercício.")


class ItemTreino:
    """Um exercício dentro da ficha, com séries, repetições, carga e descanso."""

    def __init__(self, exercicio_id, series, repeticoes, carga_kg=None, descanso_seg=60,
                 observacao="", ordem=None, id=None, exercicio_nome=None, grupo_nome=None,
                 equipamento=None, instrucoes=None):
        try:
            self.exercicio_id = int(exercicio_id)
        except (TypeError, ValueError):
            raise ValidacaoErro("Escolha o exercício em todas as linhas do treino.")
        self.series = series
        self.repeticoes = repeticoes
        self.carga_kg = carga_kg
        self.descanso_seg = descanso_seg
        self.observacao = (observacao or "").strip()[:120]
        self.ordem = ordem
        self.id = id
        self.exercicio_nome = exercicio_nome
        self.grupo_nome = grupo_nome
        self.equipamento = equipamento
        self.instrucoes = instrucoes

    @property
    def series(self):
        return self._series

    @series.setter
    def series(self, valor):
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            raise ValidacaoErro("Número de séries inválido.")
        if not 1 <= valor <= 10:
            raise ValidacaoErro("As séries devem ser de 1 a 10.")
        self._series = valor

    @property
    def repeticoes(self):
        return self._repeticoes

    @repeticoes.setter
    def repeticoes(self, valor):
        valor = (str(valor) if valor is not None else "").strip()
        if not valor or len(valor) > 20:
            raise ValidacaoErro("Informe as repetições (ex.: 12, 10-12 ou 30s).")
        self._repeticoes = valor

    @property
    def carga_kg(self):
        return self._carga

    @carga_kg.setter
    def carga_kg(self, valor):
        if valor in (None, ""):
            self._carga = None
            return
        try:
            valor = round(float(str(valor).replace(",", ".")), 1)
        except (TypeError, ValueError):
            raise ValidacaoErro("Carga inválida.")
        if valor < 0 or valor > 500:
            raise ValidacaoErro("A carga deve ficar entre 0 e 500 kg.")
        self._carga = valor

    @property
    def descanso_seg(self):
        return self._descanso

    @descanso_seg.setter
    def descanso_seg(self, valor):
        try:
            valor = int(valor if valor not in (None, "") else 60)
        except (TypeError, ValueError):
            raise ValidacaoErro("Descanso inválido.")
        if not 0 <= valor <= 600:
            raise ValidacaoErro("O descanso deve ficar entre 0 e 600 segundos.")
        self._descanso = valor

    @property
    def prescricao(self):
        return f"{self._series} × {self._repeticoes}"

    @property
    def carga_texto(self):
        if self._carga is None:
            return "—"
        return f"{self._carga:g} kg".replace(".", ",")

    @property
    def descanso_texto(self):
        minutos, segundos = divmod(self._descanso, 60)
        if minutos and segundos:
            return f"{minutos}min{segundos:02d}"
        return f"{minutos}min" if minutos else f"{segundos}s"


class Treino(Entidade):
    """Ficha de treino (ex.: "Treino A - Peito e Tríceps") montada pelo personal para um aluno."""

    MAX_EXERCICIOS = 20

    def __init__(self, aluno_id, personal_id, nome, observacoes="", ativo=True, id=None,
                 criado_em=None, atualizado_em=None, personal_nome=None, aluno_nome=None):
        super().__init__(id)
        self.aluno_id = aluno_id
        self.personal_id = personal_id
        self.nome = nome
        self.observacoes = (observacoes or "").strip()
        self.ativo = bool(ativo)
        self.criado_em = criado_em
        self.atualizado_em = atualizado_em
        self.personal_nome = personal_nome
        self.aluno_nome = aluno_nome
        self._itens = []

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valor):
        valor = (valor or "").strip()
        if len(valor) < 2:
            raise ValidacaoErro("Dê um nome ao treino (ex.: Treino A - Peito e Tríceps).")
        self._nome = valor[:80]

    # ---------------- itens (composição) ----------------
    @property
    def itens(self):
        return list(self._itens)

    def adicionar_item(self, item):
        if len(self._itens) >= self.MAX_EXERCICIOS:
            raise ValidacaoErro(f"Um treino pode ter no máximo {self.MAX_EXERCICIOS} exercícios.")
        item.ordem = len(self._itens) + 1
        self._itens.append(item)

    def definir_itens(self, itens):
        self._itens = []
        for item in itens:
            self.adicionar_item(item)

    @property
    def total_series(self):
        return sum(i.series for i in self._itens)

    @property
    def grupos(self):
        """Grupos musculares trabalhados, na ordem em que aparecem."""
        vistos = []
        for i in self._itens:
            if i.grupo_nome and i.grupo_nome not in vistos:
                vistos.append(i.grupo_nome)
        return vistos

    @property
    def letra(self):
        """'A' para 'Treino A - ...' (usado nas abas da área do aluno)."""
        partes = self._nome.split()
        if len(partes) >= 2 and partes[0].lower() == "treino" and len(partes[1]) == 1:
            return partes[1].upper()
        return self._nome[0].upper()

    def validar(self):
        if not self._itens:
            raise ValidacaoErro("Adicione pelo menos um exercício ao treino.")


class TreinoRealizado(Entidade):
    """Registro de um treino concluído pelo aluno (quantas séries fez e quanto tempo levou)."""

    def __init__(self, aluno_id, treino_id, data, series_feitas, series_total, duracao_min, id=None,
                 criado_em=None, treino_nome=None):
        from utils import para_data
        super().__init__(id)
        self.aluno_id = aluno_id
        self.treino_id = treino_id
        self.data = para_data(data)
        try:
            self.series_total = int(series_total)
            self.series_feitas = int(series_feitas)
            self.duracao_min = int(duracao_min)
        except (TypeError, ValueError):
            raise ValidacaoErro("Dados do treino realizado inválidos.")
        self.criado_em = criado_em
        self.treino_nome = treino_nome

    @property
    def percentual(self):
        return round(100 * self.series_feitas / self.series_total) if self.series_total else 0

    @property
    def completo(self):
        return self.series_feitas >= self.series_total

    @property
    def letra(self):
        partes = (self.treino_nome or "").split()
        if len(partes) >= 2 and partes[0].lower() == "treino" and len(partes[1]) == 1:
            return partes[1].upper()
        return (self.treino_nome or "?")[0].upper()

    def validar(self):
        if self.series_feitas < 1:
            raise ValidacaoErro("Marque pelo menos uma série antes de finalizar o treino.")
        if self.series_feitas > self.series_total:
            raise ValidacaoErro("Número de séries maior que o do treino.")
        if not 1 <= self.duracao_min <= 300:
            raise ValidacaoErro("Duração do treino inválida.")

    def para_dict(self):
        return {"nome": self.treino_nome, "letra": self.letra, "series_feitas": self.series_feitas,
                "series_total": self.series_total, "duracao": self.duracao_min, "percentual": self.percentual}
