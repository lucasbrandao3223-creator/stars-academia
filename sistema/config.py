"""Configurações gerais do sistema da academia."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Caminho do arquivo do banco SQLite (pode ser trocado pela variável de ambiente)
DATABASE_PATH = os.environ.get("ACADEMIA_DB", os.path.join(BASE_DIR, "academia.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

# Chave usada pelo Flask para assinar a sessão (login)
SECRET_KEY = os.environ.get("ACADEMIA_SECRET", "academia-forca-total-chave-de-desenvolvimento")

# Regras de negócio
DIAS_PARA_RENOVAR = 15        # a renovação fica liberada nos últimos X dias do plano
DIAS_ALERTA_VENCIMENTO = 7    # painel avisa matrículas que vencem em até X dias
