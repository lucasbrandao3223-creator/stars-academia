from datetime import timedelta

from models.matricula import Checkin, Matricula
from repositories.base import RepositorioBase
from utils import DIAS_CURTOS, MESES_CURTOS, para_data


class MatriculaRepositorio(RepositorioBase):
    TABELA = "matricula"
    NOME_ENTIDADE = "Matrícula"

    SQL_BASE = """
        SELECT m.*, u.nome AS aluno_nome, u.telefone AS aluno_telefone, p.nome AS plano_nome
          FROM matricula m
          JOIN usuario u ON u.id = m.aluno_id
          JOIN plano   p ON p.id = m.plano_id"""

    # condição SQL de cada situação (a situação é calculada a partir das datas)
    FILTROS = {
        "ativa": "m.status = 'ativa' AND m.data_inicio <= :hoje AND m.data_fim >= :hoje",
        "vencendo": "m.status = 'ativa' AND m.data_inicio <= :hoje AND m.data_fim BETWEEN :hoje AND :limite "
                    "AND NOT EXISTS (SELECT 1 FROM matricula r WHERE r.aluno_id = m.aluno_id "
                    "AND r.status = 'ativa' AND r.data_inicio > m.data_fim)",
        "agendada": "m.status = 'ativa' AND m.data_inicio > :hoje",
        "vencida": "m.status = 'ativa' AND m.data_fim < :hoje",
        "cancelada": "m.status = 'cancelada'",
    }

    def _para_objeto(self, linha):
        return Matricula(**{k: linha[k] for k in linha.keys()})

    def buscar_por_id(self, id):
        linha = self._consultar_um(self.SQL_BASE + " WHERE m.id = ?", (id,))
        return self._para_objeto(linha) if linha else None

    def listar_do_aluno(self, aluno_id):
        return self._lista(self._consultar(
            self.SQL_BASE + " WHERE m.aluno_id = ? ORDER BY m.data_inicio DESC, m.id DESC", (aluno_id,)))

    def listar(self, hoje, situacao=None, busca=None, dias_alerta=7):
        sql = self.SQL_BASE + " WHERE 1 = 1"
        parametros = {"hoje": hoje.isoformat(), "limite": (hoje + timedelta(days=dias_alerta)).isoformat()}
        if situacao in self.FILTROS:
            sql += " AND " + self.FILTROS[situacao]
        if busca:
            sql += " AND u.nome LIKE :busca"
            parametros["busca"] = f"%{busca.strip()}%"
        ordem = "m.data_fim ASC" if situacao in ("vencendo", "ativa") else "m.data_inicio DESC"
        return self._lista(self._consultar(sql + f" ORDER BY {ordem}, m.id DESC LIMIT 300", parametros))

    def vigentes(self, hoje):
        """Todas as matrículas válidas hoje (sem limite de linhas)."""
        return self._lista(self._consultar(
            self.SQL_BASE + " WHERE m.status = 'ativa' AND ? BETWEEN m.data_inicio AND m.data_fim",
            (para_data(hoje).isoformat(),)))

    def vigente_do_aluno(self, aluno_id, data):
        """Matrícula que permite treinar nessa data (ou None)."""
        linha = self._consultar_um(
            self.SQL_BASE + " WHERE m.aluno_id = ? AND m.status = 'ativa' AND ? BETWEEN m.data_inicio AND m.data_fim",
            (aluno_id, para_data(data).isoformat()))
        return self._para_objeto(linha) if linha else None

    def agendada_do_aluno(self, aluno_id, hoje):
        linha = self._consultar_um(
            self.SQL_BASE + " WHERE m.aluno_id = ? AND m.status = 'ativa' AND m.data_inicio > ? "
            "ORDER BY m.data_inicio LIMIT 1", (aluno_id, para_data(hoje).isoformat()))
        return self._para_objeto(linha) if linha else None

    def salvar(self, m):
        m.validar()
        if m.eh_novo:
            cursor = self._executar(
                """INSERT INTO matricula (aluno_id, plano_id, data_inicio, data_fim, valor_total, forma_pagamento, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (m.aluno_id, m.plano_id, m.data_inicio.isoformat(), m.data_fim.isoformat(), m.valor_total,
                 m.forma_pagamento.value, m.status))
            m.id = cursor.lastrowid
        else:
            self._executar("UPDATE matricula SET status = ? WHERE id = ?", (m.status, m.id))
        return m

    # ---------------- relatórios ----------------
    def estatisticas(self, hoje, dias_alerta=7):
        p = {"hoje": hoje.isoformat(), "limite": (hoje + timedelta(days=dias_alerta)).isoformat(),
             "mes": hoje.strftime("%Y-%m")}
        linha = self._consultar_um(f"""
            SELECT
              (SELECT COUNT(DISTINCT m.aluno_id) FROM matricula m WHERE {self.FILTROS['ativa']})  AS alunos_ativos,
              (SELECT COUNT(*) FROM matricula m WHERE {self.FILTROS['vencendo']})                 AS vencendo,
              (SELECT COALESCE(SUM(valor_total), 0) FROM matricula
                WHERE status <> 'cancelada' AND substr(data_inicio, 1, 7) = :mes)                 AS faturamento_mes,
              (SELECT COUNT(*) FROM matricula
                WHERE status <> 'cancelada' AND substr(data_inicio, 1, 7) = :mes)                 AS matriculas_mes,
              (SELECT COUNT(*) FROM aluno)                                                        AS total_alunos""", p)
        return {k: linha[k] for k in linha.keys()}

    def faturamento_mensal(self, hoje, meses=6):
        """Lê a view vw_faturamento_mensal (até o mês atual)."""
        linhas = self._consultar("SELECT * FROM vw_faturamento_mensal WHERE mes <= ? ORDER BY mes DESC LIMIT ?",
                                 (hoje.strftime("%Y-%m"), meses))
        resultado = []
        for l in reversed(linhas):
            ano, mes = l["mes"].split("-")
            resultado.append({"rotulo": f"{MESES_CURTOS[int(mes) - 1]}/{ano[2:]}",
                              "matriculas": l["matriculas"], "faturamento": l["faturamento"]})
        return resultado


class CheckinRepositorio(RepositorioBase):
    TABELA = "checkin"
    NOME_ENTIDADE = "Check-in"

    def _para_objeto(self, linha):
        return Checkin(id=linha["id"], aluno_id=linha["aluno_id"], data=linha["data"], hora=linha["hora"],
                       aluno_nome=linha["aluno_nome"] if "aluno_nome" in linha.keys() else None)

    def salvar(self, c):
        c.validar()
        cursor = self._executar("INSERT INTO checkin (aluno_id, data, hora) VALUES (?, ?, ?)",
                                (c.aluno_id, c.data.isoformat(), c.hora.strftime("%H:%M")))
        c.id = cursor.lastrowid
        return c

    def do_aluno_no_dia(self, aluno_id, data):
        linha = self._consultar_um("SELECT * FROM checkin WHERE aluno_id = ? AND data = ?",
                                   (aluno_id, para_data(data).isoformat()))
        return self._para_objeto(linha) if linha else None

    def datas_do_aluno(self, aluno_id, inicio, fim):
        linhas = self._consultar("SELECT data FROM checkin WHERE aluno_id = ? AND data BETWEEN ? AND ?",
                                 (aluno_id, para_data(inicio).isoformat(), para_data(fim).isoformat()))
        return {para_data(l["data"]) for l in linhas}

    def ultimos_do_aluno(self, aluno_id, limite=8):
        return self._lista(self._consultar(
            "SELECT * FROM checkin WHERE aluno_id = ? ORDER BY data DESC, hora DESC LIMIT ?", (aluno_id, limite)))

    def do_aluno_no_periodo(self, aluno_id, inicio, fim):
        return self._lista(self._consultar(
            "SELECT * FROM checkin WHERE aluno_id = ? AND data BETWEEN ? AND ? ORDER BY data",
            (aluno_id, para_data(inicio).isoformat(), para_data(fim).isoformat())))

    def do_dia(self, data):
        return self._lista(self._consultar("""
            SELECT c.*, u.nome AS aluno_nome FROM checkin c JOIN usuario u ON u.id = c.aluno_id
             WHERE c.data = ? ORDER BY c.hora DESC""", (para_data(data).isoformat(),)))

    def por_dia(self, hoje, dias=14):
        inicio = hoje - timedelta(days=dias - 1)
        linhas = self._consultar("SELECT data, COUNT(*) AS total FROM checkin WHERE data BETWEEN ? AND ? GROUP BY data",
                                 (inicio.isoformat(), hoje.isoformat()))
        contagem = {l["data"]: l["total"] for l in linhas}
        return [{"data": inicio + timedelta(days=i),
                 "rotulo": DIAS_CURTOS[(inicio + timedelta(days=i)).weekday()][0],
                 "dia": (inicio + timedelta(days=i)).day,
                 "total": contagem.get((inicio + timedelta(days=i)).isoformat(), 0)} for i in range(dias)]

    def por_hora(self, hoje, dias=30):
        """Horários de pico: check-ins por hora do dia nos últimos dias."""
        inicio = hoje - timedelta(days=dias)
        linhas = self._consultar("""
            SELECT CAST(substr(hora, 1, 2) AS INTEGER) AS h, COUNT(*) AS total
              FROM checkin WHERE data BETWEEN ? AND ? GROUP BY h ORDER BY h""",
                                 (inicio.isoformat(), hoje.isoformat()))
        return [{"hora": l["h"], "total": l["total"]} for l in linhas]

    def frequencia_alunos(self, hoje):
        """Total de check-ins nos últimos 30 dias e último check-in de cada aluno."""
        inicio = (hoje - timedelta(days=29)).isoformat()
        linhas = self._consultar("""
            SELECT aluno_id, MAX(data) AS ultimo,
                   SUM(CASE WHEN data >= ? THEN 1 ELSE 0 END) AS ultimos_30
              FROM checkin GROUP BY aluno_id""", (inicio,))
        return {l["aluno_id"]: {"ultimo": para_data(l["ultimo"]), "ultimos_30": l["ultimos_30"]} for l in linhas}
