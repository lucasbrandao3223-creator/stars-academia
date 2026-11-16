"""Funções auxiliares de data, hora e formatação."""
import calendar
import re
from datetime import date, datetime, time, timedelta

DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
               "Sexta-feira", "Sábado", "Domingo"]
DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun",
                "jul", "ago", "set", "out", "nov", "dez"]


def para_data(valor):
    """Converte 'AAAA-MM-DD' (ou date) em date."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.strptime(str(valor).strip(), "%Y-%m-%d").date()


def para_hora(valor):
    """Converte 'HH:MM' (ou time) em time."""
    if isinstance(valor, time):
        return valor
    return datetime.strptime(str(valor).strip()[:5], "%H:%M").time()


def hora_str(valor):
    return para_hora(valor).strftime("%H:%M")


def em_minutos(valor):
    h = para_hora(valor)
    return h.hour * 60 + h.minute


def de_minutos(total):
    return time(total // 60, total % 60)


def somar_minutos(valor, minutos):
    base = datetime.combine(date(2000, 1, 1), para_hora(valor))
    return (base + timedelta(minutes=minutos)).time()


def formatar_moeda(valor):
    texto = f"{float(valor or 0):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_data(valor):
    return para_data(valor).strftime("%d/%m/%Y")


def formatar_duracao(minutos):
    horas, resto = divmod(int(minutos), 60)
    if horas and resto:
        return f"{horas}h {resto:02d}min"
    if horas:
        return f"{horas}h"
    return f"{resto} min"


def apenas_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def formatar_telefone(valor):
    t = apenas_digitos(valor)
    if len(t) == 11:
        return f"({t[:2]}) {t[2:7]}-{t[7:]}"
    if len(t) == 10:
        return f"({t[:2]}) {t[2:6]}-{t[6:]}"
    return t


def somar_meses(data, meses):
    """Soma meses a uma data (31/01 + 1 mês = 28 ou 29/02)."""
    total = data.month - 1 + meses
    ano, mes = data.year + total // 12, total % 12 + 1
    return date(ano, mes, min(data.day, calendar.monthrange(ano, mes)[1]))


def calcular_idade(nascimento, hoje=None):
    if not nascimento:
        return None
    nascimento = para_data(nascimento)
    hoje = hoje or date.today()
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
