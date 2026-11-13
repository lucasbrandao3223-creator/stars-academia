from models.plano import Plano
from repositories.base import RepositorioBase


class PlanoRepositorio(RepositorioBase):
    TABELA = "plano"
    NOME_ENTIDADE = "Plano"

    def _para_objeto(self, linha):
        return Plano(id=linha["id"], nome=linha["nome"], descricao=linha["descricao"],
                     duracao_meses=linha["duracao_meses"], preco_mensal=linha["preco_mensal"],
                     ativo=linha["ativo"])

    def listar(self, apenas_ativos=True):
        sql = "SELECT * FROM plano"
        if apenas_ativos:
            sql += " WHERE ativo = 1"
        return self._lista(self._consultar(sql + " ORDER BY ativo DESC, duracao_meses"))

    def salvar(self, plano):
        plano.validar()
        dados = (plano.nome, plano.descricao, plano.duracao_meses, plano.preco_mensal, int(plano.ativo))
        if plano.eh_novo:
            cursor = self._executar(
                "INSERT INTO plano (nome, descricao, duracao_meses, preco_mensal, ativo) VALUES (?, ?, ?, ?, ?)", dados)
            plano.id = cursor.lastrowid
        else:
            self._executar(
                "UPDATE plano SET nome = ?, descricao = ?, duracao_meses = ?, preco_mensal = ?, ativo = ? WHERE id = ?",
                dados + (plano.id,))
        return plano

    def alunos_por_plano(self, hoje):
        """Quantos alunos estão com matrícula vigente em cada plano (gráfico do painel)."""
        return self._consultar("""
            SELECT p.nome, COUNT(m.id) AS total
              FROM plano p
              LEFT JOIN matricula m ON m.plano_id = p.id AND m.status = 'ativa'
                                   AND ? BETWEEN m.data_inicio AND m.data_fim
             GROUP BY p.id, p.nome
             ORDER BY p.duracao_meses""", (hoje.isoformat(),))
