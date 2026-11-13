"""Classe base dos repositórios (padrão DAO / Repository)."""
import sqlite3
from abc import ABC, abstractmethod

from exceptions import NaoEncontradoErro, ValidacaoErro


class RepositorioBase(ABC):
    """Concentra o SQL comum. Cada repositório filho informa sua TABELA
    e implementa _para_objeto(), que transforma uma linha do banco em objeto."""

    TABELA = None
    NOME_ENTIDADE = "Registro"

    def __init__(self, conexao):
        self._conn = conexao

    @abstractmethod
    def _para_objeto(self, linha):
        """Converte sqlite3.Row -> objeto do model."""

    # ---------------- helpers ----------------
    def _consultar(self, sql, parametros=()):
        return self._conn.execute(sql, parametros).fetchall()

    def _consultar_um(self, sql, parametros=()):
        return self._conn.execute(sql, parametros).fetchone()

    def _executar(self, sql, parametros=()):
        try:
            cursor = self._conn.execute(sql, parametros)
            self._conn.commit()
            return cursor
        except sqlite3.IntegrityError as erro:
            self._conn.rollback()
            raise ValidacaoErro(self._traduzir_erro(erro)) from erro

    @staticmethod
    def _traduzir_erro(erro):
        texto = str(erro)
        if "UNIQUE" in texto and "email" in texto:
            return "Este e-mail já está cadastrado."
        if "UNIQUE" in texto and "cref" in texto:
            return "Já existe um personal com esse CREF."
        if "UNIQUE" in texto and "checkin" in texto:
            return "Check-in de hoje já foi feito."
        if "UNIQUE" in texto and ".nome" in texto:
            return "Já existe um cadastro com esse nome."
        if "matrícula" in texto or "Check-in" in texto:
            return texto
        return "Não foi possível salvar: dados inválidos."

    def _lista(self, linhas):
        return [self._para_objeto(l) for l in linhas]

    # ---------------- operações genéricas ----------------
    def buscar_por_id(self, id):
        linha = self._consultar_um(f"SELECT * FROM {self.TABELA} WHERE id = ?", (id,))
        return self._para_objeto(linha) if linha else None

    def obter(self, id):
        """Igual a buscar_por_id, mas lança erro se não existir."""
        objeto = self.buscar_por_id(id)
        if objeto is None:
            raise NaoEncontradoErro(f"{self.NOME_ENTIDADE} não encontrado(a).")
        return objeto

    def listar_todos(self):
        return self._lista(self._consultar(f"SELECT * FROM {self.TABELA} ORDER BY id"))

    def contar(self):
        return self._consultar_um(f"SELECT COUNT(*) AS total FROM {self.TABELA}")["total"]
