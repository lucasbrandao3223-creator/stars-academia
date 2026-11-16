from exceptions import NaoEncontradoErro
from models.academia import Academia, HorarioFuncionamento
from repositories.base import RepositorioBase


class AcademiaRepositorio(RepositorioBase):
    TABELA = "academia"
    NOME_ENTIDADE = "Academia"

    def _para_objeto(self, linha):
        academia = Academia(**{k: linha[k] for k in linha.keys()})
        for h in self._consultar("SELECT * FROM horario_funcionamento ORDER BY dia_semana"):
            academia.definir_horario(HorarioFuncionamento(h["dia_semana"], h["abertura"], h["fechamento"]))
        return academia

    def carregar(self):
        linha = self._consultar_um("SELECT * FROM academia WHERE id = 1")
        return self._para_objeto(linha) if linha else None

    def obter(self, id=1):
        academia = self.carregar()
        if academia is None:
            raise NaoEncontradoErro("Os dados da academia não foram cadastrados.")
        return academia

    def salvar(self, a):
        a.validar()
        self._conn.execute(
            """INSERT INTO academia (id, nome, slogan, descricao, endereco, cidade, telefone, whatsapp, instagram)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET nome = excluded.nome, slogan = excluded.slogan,
                   descricao = excluded.descricao, endereco = excluded.endereco, cidade = excluded.cidade,
                   telefone = excluded.telefone, whatsapp = excluded.whatsapp, instagram = excluded.instagram""",
            (a.nome, a.slogan, a.descricao, a.endereco, a.cidade, a.telefone, a.whatsapp, a.instagram))
        self._conn.execute("DELETE FROM horario_funcionamento")
        self._conn.executemany(
            "INSERT INTO horario_funcionamento (dia_semana, abertura, fechamento) VALUES (?, ?, ?)",
            [(h.dia_semana, h.abertura.strftime("%H:%M"), h.fechamento.strftime("%H:%M")) for h in a.horarios])
        self._conn.commit()
        return a
