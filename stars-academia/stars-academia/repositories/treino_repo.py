import sqlite3

from exceptions import ValidacaoErro
from models.treino import Exercicio, GrupoMuscular, ItemTreino, Treino, TreinoRealizado
from utils import para_data
from repositories.base import RepositorioBase


class GrupoMuscularRepositorio(RepositorioBase):
    TABELA = "grupo_muscular"
    NOME_ENTIDADE = "Grupo muscular"

    def _para_objeto(self, linha):
        return GrupoMuscular(id=linha["id"], nome=linha["nome"])


class ExercicioRepositorio(RepositorioBase):
    TABELA = "exercicio"
    NOME_ENTIDADE = "Exercício"

    SQL_BASE = """SELECT e.*, g.nome AS grupo_nome,
                         (SELECT COUNT(*) FROM treino_exercicio te WHERE te.exercicio_id = e.id) AS usos
                    FROM exercicio e JOIN grupo_muscular g ON g.id = e.grupo_muscular_id"""

    def _para_objeto(self, linha):
        ex = Exercicio(id=linha["id"], nome=linha["nome"], grupo_muscular_id=linha["grupo_muscular_id"],
                       equipamento=linha["equipamento"], instrucoes=linha["instrucoes"],
                       grupo_nome=linha["grupo_nome"])
        ex.usos = linha["usos"]
        return ex

    def buscar_por_id(self, id):
        linha = self._consultar_um(self.SQL_BASE + " WHERE e.id = ?", (id,))
        return self._para_objeto(linha) if linha else None

    def listar(self, grupo_id=None):
        sql = self.SQL_BASE
        parametros = []
        if grupo_id:
            sql += " WHERE e.grupo_muscular_id = ?"
            parametros.append(int(grupo_id))
        return self._lista(self._consultar(sql + " ORDER BY g.id, e.nome", parametros))

    def salvar(self, ex):
        ex.validar()
        dados = (ex.nome, ex.grupo_muscular_id, ex.equipamento, ex.instrucoes)
        if ex.eh_novo:
            cursor = self._executar(
                "INSERT INTO exercicio (nome, grupo_muscular_id, equipamento, instrucoes) VALUES (?, ?, ?, ?)", dados)
            ex.id = cursor.lastrowid
        else:
            self._executar("UPDATE exercicio SET nome = ?, grupo_muscular_id = ?, equipamento = ?, instrucoes = ? "
                           "WHERE id = ?", dados + (ex.id,))
        return ex

    def excluir(self, id):
        self._executar("DELETE FROM exercicio WHERE id = ?", (id,))


class TreinoRepositorio(RepositorioBase):
    TABELA = "treino"
    NOME_ENTIDADE = "Treino"

    SQL_BASE = """SELECT t.*, pu.nome AS personal_nome, au.nome AS aluno_nome
                    FROM treino t
                    JOIN usuario pu ON pu.id = t.personal_id
                    JOIN usuario au ON au.id = t.aluno_id"""

    def _para_objeto(self, linha):
        treino = Treino(**{k: linha[k] for k in linha.keys()})
        itens = self._consultar("""
            SELECT te.*, e.nome AS exercicio_nome, g.nome AS grupo_nome, e.equipamento, e.instrucoes
              FROM treino_exercicio te
              JOIN exercicio e      ON e.id = te.exercicio_id
              JOIN grupo_muscular g ON g.id = e.grupo_muscular_id
             WHERE te.treino_id = ? ORDER BY te.ordem""", (treino.id,))
        treino.definir_itens([ItemTreino(**{k: i[k] for k in i.keys() if k != "treino_id"}) for i in itens])
        return treino

    def buscar_por_id(self, id):
        linha = self._consultar_um(self.SQL_BASE + " WHERE t.id = ?", (id,))
        return self._para_objeto(linha) if linha else None

    def listar_do_aluno(self, aluno_id, apenas_ativos=True):
        sql = self.SQL_BASE + " WHERE t.aluno_id = ?"
        if apenas_ativos:
            sql += " AND t.ativo = 1"
        return self._lista(self._consultar(sql + " ORDER BY t.ativo DESC, t.nome", (aluno_id,)))

    def contar_ativos_por_aluno(self):
        return {l["aluno_id"]: l["total"] for l in self._consultar(
            "SELECT aluno_id, COUNT(*) AS total FROM treino WHERE ativo = 1 GROUP BY aluno_id")}

    def salvar(self, treino):
        """Grava o treino e substitui a lista de exercícios numa única transação."""
        treino.validar()
        try:
            if treino.eh_novo:
                cursor = self._conn.execute(
                    "INSERT INTO treino (aluno_id, personal_id, nome, observacoes, ativo) VALUES (?, ?, ?, ?, ?)",
                    (treino.aluno_id, treino.personal_id, treino.nome, treino.observacoes, int(treino.ativo)))
                treino_id = cursor.lastrowid
            else:
                treino_id = treino.id
                self._conn.execute(
                    "UPDATE treino SET personal_id = ?, nome = ?, observacoes = ?, ativo = ?, "
                    "atualizado_em = datetime('now', 'localtime') WHERE id = ?",
                    (treino.personal_id, treino.nome, treino.observacoes, int(treino.ativo), treino.id))
            self._conn.execute("DELETE FROM treino_exercicio WHERE treino_id = ?", (treino_id,))
            self._conn.executemany(
                """INSERT INTO treino_exercicio
                   (treino_id, exercicio_id, ordem, series, repeticoes, carga_kg, descanso_seg, observacao)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(treino_id, i.exercicio_id, i.ordem, i.series, i.repeticoes, i.carga_kg, i.descanso_seg,
                  i.observacao) for i in treino.itens])
            self._conn.commit()
        except sqlite3.IntegrityError as erro:
            self._conn.rollback()
            raise ValidacaoErro(self._traduzir_erro(erro)) from erro
        if treino.eh_novo:
            treino.id = treino_id
        return treino

    def alterar_ativo(self, treino):
        self._executar("UPDATE treino SET ativo = ? WHERE id = ?", (int(treino.ativo), treino.id))
        return treino


class TreinoRealizadoRepositorio(RepositorioBase):
    TABELA = "treino_realizado"
    NOME_ENTIDADE = "Treino realizado"

    SQL_BASE = """SELECT r.*, t.nome AS treino_nome FROM treino_realizado r JOIN treino t ON t.id = r.treino_id"""

    def _para_objeto(self, linha):
        return TreinoRealizado(**{k: linha[k] for k in linha.keys()})

    def salvar(self, r):
        r.validar()
        cursor = self._executar(
            "INSERT INTO treino_realizado (aluno_id, treino_id, data, series_feitas, series_total, duracao_min) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (r.aluno_id, r.treino_id, r.data.isoformat(), r.series_feitas, r.series_total, r.duracao_min))
        r.id = cursor.lastrowid
        return r

    def do_treino_no_dia(self, treino_id, data):
        linha = self._consultar_um(self.SQL_BASE + " WHERE r.treino_id = ? AND r.data = ?",
                                   (treino_id, para_data(data).isoformat()))
        return self._para_objeto(linha) if linha else None

    def do_aluno_no_periodo(self, aluno_id, inicio, fim):
        """{data: [treinos realizados]} no período."""
        linhas = self._consultar(self.SQL_BASE + " WHERE r.aluno_id = ? AND r.data BETWEEN ? AND ? ORDER BY r.id",
                                 (aluno_id, para_data(inicio).isoformat(), para_data(fim).isoformat()))
        resultado = {}
        for l in linhas:
            r = self._para_objeto(l)
            resultado.setdefault(r.data, []).append(r)
        return resultado

    def ultimos_do_aluno(self, aluno_id, limite=8):
        return self._lista(self._consultar(
            self.SQL_BASE + " WHERE r.aluno_id = ? ORDER BY r.data DESC, r.id DESC LIMIT ?", (aluno_id, limite)))

    def ultimo_por_treino(self, aluno_id):
        """{treino_id: data do último treino realizado}."""
        return {l["treino_id"]: para_data(l["ultima"]) for l in self._consultar(
            "SELECT treino_id, MAX(data) AS ultima FROM treino_realizado WHERE aluno_id = ? GROUP BY treino_id",
            (aluno_id,))}

    def totais_do_aluno(self, aluno_id):
        linha = self._consultar_um(
            "SELECT COUNT(*) AS treinos, COALESCE(SUM(duracao_min), 0) AS minutos, "
            "COALESCE(SUM(series_feitas), 0) AS series FROM treino_realizado WHERE aluno_id = ?", (aluno_id,))
        return {k: linha[k] for k in linha.keys()}
