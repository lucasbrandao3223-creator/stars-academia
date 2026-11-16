"""Recria o banco da academia do zero com os dados de demonstração.

Uso:  python sistema/init_db.py   (rodando da pasta principal do projeto)
"""
from conexao import BancoDeDados
from seed import popular


def recriar_banco(caminho=None):
    banco = BancoDeDados(caminho)
    banco.criar_estrutura()
    conexao = banco.conectar()
    try:
        popular(conexao)
    finally:
        conexao.close()
    return banco.caminho


if __name__ == "__main__":
    caminho = recriar_banco()
    print(f"Banco criado com dados de exemplo em: {caminho}")
