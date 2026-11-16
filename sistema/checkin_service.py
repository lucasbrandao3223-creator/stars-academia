"""Check-in na academia e cálculo de frequência."""
import calendar
from datetime import datetime, timedelta

from exceptions import CheckinErro, PermissaoNegadaErro
from matricula import Checkin
from usuario import Aluno
from academia_repo import AcademiaRepositorio
from matricula_repo import CheckinRepositorio, MatriculaRepositorio
from treino_repo import TreinoRealizadoRepositorio
from utils import hora_str

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]


class CheckinService:

    def __init__(self, conexao, relogio=datetime.now):
        self._agora = relogio
        self.academia = AcademiaRepositorio(conexao)
        self.checkins = CheckinRepositorio(conexao)
        self.matriculas = MatriculaRepositorio(conexao)
        self.realizados = TreinoRealizadoRepositorio(conexao)

    # ------------------------------------------------------------------
    def situacao_hoje(self, aluno):
        """O que mostrar no botão de check-in da área do aluno."""
        agora = self._agora()
        feito = self.checkins.do_aluno_no_dia(aluno.id, agora.date())
        if feito:
            return {"pode": False, "feito": feito, "mensagem": f"Check-in feito hoje às {feito.hora_texto}. Bom treino!"}
        try:
            self._validar(aluno, agora)
        except CheckinErro as erro:
            return {"pode": False, "feito": None, "mensagem": str(erro)}
        return {"pode": True, "feito": None, "mensagem": "Chegou na academia? Faça o check-in."}

    def fazer_checkin(self, usuario):
        if not isinstance(usuario, Aluno):
            raise PermissaoNegadaErro("Somente alunos fazem check-in.")
        agora = self._agora()
        feito = self.checkins.do_aluno_no_dia(usuario.id, agora.date())
        if feito:
            raise CheckinErro(f"Você já fez check-in hoje às {feito.hora_texto}.")
        self._validar(usuario, agora)
        return self.checkins.salvar(Checkin(aluno_id=usuario.id, data=agora.date(), hora=agora.time()))

    def _validar(self, aluno, agora):
        if self.matriculas.vigente_do_aluno(aluno.id, agora.date()) is None:
            raise CheckinErro("Você precisa de um plano ativo para fazer check-in.")
        academia = self.academia.obter()
        if not academia.esta_aberta(agora):
            horario = academia.horario_do_dia(agora.weekday())
            if horario is None:
                raise CheckinErro("Hoje a academia não abre.")
            raise CheckinErro(f"A academia está fechada agora. Hoje abre das {hora_str(horario.abertura)} "
                              f"às {hora_str(horario.fechamento)}.")

    # ------------------------------------------------------------------
    def frequencia(self, aluno_id, ano=None, mes=None, meta_semanal=3):
        """Monta tudo que a tela de frequência precisa (vai para o JavaScript em JSON)."""
        hoje = self._agora().date()
        ano = ano or hoje.year
        mes = mes or hoje.month
        if not 1 <= mes <= 12:
            raise ValueError("Mês inválido.")

        # todos os dias em que o aluno fez check-in (último ano, para a sequência e os gráficos)
        datas_treino = self.checkins.datas_do_aluno(aluno_id, hoje - timedelta(days=400), hoje)
        dias_no_mes = [d for d in datas_treino if d.year == ano and d.month == mes]
        ultimos_30 = [d for d in datas_treino if d >= hoje - timedelta(days=29)]

        semana_atual = self._semana_atual(datas_treino, hoje)
        return {
            "titulo": f"{MESES[mes - 1]} de {ano}",
            "semanas": self._calendario_do_mes(aluno_id, ano, mes, datas_treino, hoje),
            "no_mes": len(dias_no_mes),
            "ultimos_30": len(ultimos_30),
            "media_semanal": round(len(ultimos_30) / 30 * 7, 1),
            "sequencia": self._sequencia(datas_treino, hoje),
            "semana_atual": semana_atual,
            "feitos_semana": len([d for d in semana_atual if d["treinou"]]),
            "meta_semanal": meta_semanal,
            "evolucao": self._evolucao_semanal(datas_treino, hoje),
            "anterior": mes_vizinho(ano, mes, -1),
            "proximo": mes_vizinho(ano, mes, +1) if (ano, mes) < (hoje.year, hoje.month) else None,
        }

    def _calendario_do_mes(self, aluno_id, ano, mes, datas_treino, hoje):
        """Lista de semanas; cada semana é uma lista de 7 dias com o que aconteceu em cada um."""
        semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(ano, mes)   # começa na segunda
        primeiro_dia, ultimo_dia = semanas[0][0], semanas[-1][-1]
        academia = self.academia.obter()

        # horário do check-in e treinos feitos em cada dia do mês
        horas = {}
        for c in self.checkins.do_aluno_no_periodo(aluno_id, primeiro_dia, ultimo_dia):
            horas[c.data] = c.hora_texto
        treinos = self.realizados.do_aluno_no_periodo(aluno_id, primeiro_dia, ultimo_dia)

        resultado = []
        for semana in semanas:
            dias = []
            for dia in semana:
                dias.append({
                    "data": dia.isoformat(),
                    "dia": dia.day,
                    "treinou": dia in datas_treino,
                    "hora": horas.get(dia),
                    "hoje": dia == hoje,
                    "fora": dia.month != mes,                                   # dia de outro mês
                    "futuro": dia > hoje,
                    "fechado": academia.horario_do_dia(dia.weekday()) is None,  # academia não abre
                    "treinos": [t.para_dict() for t in treinos.get(dia, [])],
                })
            resultado.append(dias)
        return resultado

    @staticmethod
    def _semana_atual(datas_treino, hoje):
        """Os 7 dias da semana atual (segunda a domingo), marcando os dias com treino."""
        segunda = hoje - timedelta(days=hoje.weekday())
        dias = []
        for i in range(7):
            dia = segunda + timedelta(days=i)
            dias.append({"rotulo": "STQQSSD"[i], "data": dia.isoformat(),
                         "treinou": dia in datas_treino, "hoje": dia == hoje})
        return dias

    @staticmethod
    def _evolucao_semanal(datas_treino, hoje):
        """Quantos treinos o aluno fez em cada uma das últimas 8 semanas (para o gráfico)."""
        segunda_atual = hoje - timedelta(days=hoje.weekday())
        semanas = []
        for semanas_atras in range(7, -1, -1):
            inicio = segunda_atual - timedelta(weeks=semanas_atras)
            fim = inicio + timedelta(days=6)
            total = len([d for d in datas_treino if inicio <= d <= fim])
            semanas.append({"rotulo": inicio.strftime("%d/%m"), "total": total, "atual": semanas_atras == 0})
        return semanas

    def _sequencia(self, datas_treino, hoje):
        """Dias seguidos de treino até hoje. Dias em que a academia fecha não quebram a sequência."""
        academia = self.academia.obter()
        dia = hoje if hoje in datas_treino else hoje - timedelta(days=1)
        total = 0
        while total < 400:
            if academia.horario_do_dia(dia.weekday()) is None:   # academia fechada: pula
                dia -= timedelta(days=1)
                continue
            if dia not in datas_treino:                           # faltou: acabou a sequência
                break
            total += 1
            dia -= timedelta(days=1)
        return total


def mes_vizinho(ano, mes, deslocamento):
    """Mês anterior (-1) ou seguinte (+1). Ex.: (2026, 1, -1) -> {"ano": 2025, "mes": 12}."""
    mes += deslocamento
    if mes == 0:
        ano, mes = ano - 1, 12
    elif mes == 13:
        ano, mes = ano + 1, 1
    return {"ano": ano, "mes": mes}
