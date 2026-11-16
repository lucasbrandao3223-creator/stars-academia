"""Academia e HorarioFuncionamento."""
from datetime import datetime

from exceptions import ValidacaoErro
from entidade import Entidade
from utils import DIAS_CURTOS, DIAS_SEMANA, apenas_digitos, formatar_telefone, hora_str, para_hora


class HorarioFuncionamento:
    """Objeto de valor: horário de um dia da semana (0 = segunda ... 6 = domingo)."""

    def __init__(self, dia_semana, abertura, fechamento):
        dia_semana = int(dia_semana)
        if not 0 <= dia_semana <= 6:
            raise ValidacaoErro("Dia da semana inválido.")
        self.dia_semana = dia_semana
        self.abertura = para_hora(abertura)
        self.fechamento = para_hora(fechamento)
        if self.abertura >= self.fechamento:
            raise ValidacaoErro(f"{self.nome_dia}: a abertura deve ser antes do fechamento.")

    @property
    def nome_dia(self):
        return DIAS_SEMANA[self.dia_semana]

    @property
    def nome_curto(self):
        return DIAS_CURTOS[self.dia_semana]

    @property
    def texto(self):
        return f"{hora_str(self.abertura)} às {hora_str(self.fechamento)}"

    def contem(self, hora):
        return self.abertura <= para_hora(hora) < self.fechamento


class Academia(Entidade):
    """Os dados da academia (um único registro, id = 1)."""

    def __init__(self, nome, slogan="", descricao="", endereco="", cidade="", telefone="",
                 whatsapp="", instagram="", id=1):
        super().__init__(id)
        self.nome = nome
        self.slogan = slogan or ""
        self.descricao = descricao or ""
        self.endereco = endereco or ""
        self.cidade = cidade or ""
        self.telefone = apenas_digitos(telefone)
        self.whatsapp = apenas_digitos(whatsapp)
        self.instagram = instagram or ""
        self._horarios = {}

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valor):
        valor = (valor or "").strip()
        if len(valor) < 3:
            raise ValidacaoErro("O nome da academia precisa ter pelo menos 3 letras.")
        self._nome = valor

    @property
    def telefone_formatado(self):
        return formatar_telefone(self.telefone)

    @property
    def whatsapp_formatado(self):
        return formatar_telefone(self.whatsapp)

    @property
    def link_whatsapp(self):
        return f"https://wa.me/55{self.whatsapp}" if self.whatsapp else None

    @property
    def link_instagram(self):
        usuario = self.instagram.strip().lstrip("@")
        return f"https://instagram.com/{usuario}" if usuario else None

    # ---------------- horários (composição) ----------------
    @property
    def horarios(self):
        return [self._horarios[d] for d in sorted(self._horarios)]

    def definir_horario(self, horario):
        self._horarios[horario.dia_semana] = horario

    def limpar_horarios(self):
        self._horarios = {}

    def horario_do_dia(self, dia_semana):
        return self._horarios.get(dia_semana)

    def esta_aberta(self, momento=None):
        momento = momento or datetime.now()
        horario = self._horarios.get(momento.weekday())
        return horario is not None and horario.contem(momento.time())

    def grade_semana(self):
        return [(DIAS_SEMANA[d], self._horarios.get(d)) for d in range(7)]

    def validar(self):
        if not self._horarios:
            raise ValidacaoErro("A academia precisa abrir em pelo menos um dia da semana.")
