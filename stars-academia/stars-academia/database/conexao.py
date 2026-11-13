"""Acesso ao banco SQLite."""
import os
import sqlite3

import config


class BancoDeDados:
    """Responsável por abrir conexões e criar a estrutura do banco."""

    def __init__(self, caminho=None):
        self.caminho = caminho or config.DATABASE_PATH

    def conectar(self):
        conexao = sqlite3.connect(self.caminho)
        conexao.row_factory = sqlite3.Row          # acessar colunas pelo nome
        conexao.execute("PRAGMA foreign_keys = ON")  # SQLite precisa ligar as FKs
        return conexao

    def existe(self):
        return os.path.exists(self.caminho)

    def criar_estrutura(self):
        pasta = os.path.dirname(self.caminho)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        with open(config.SCHEMA_PATH, encoding="utf-8") as arquivo:
            script = arquivo.read()
        conexao = self.conectar()
        try:
            conexao.executescript(script)
            conexao.commit()
        finally:
            conexao.close()
