"""Exceções personalizadas do sistema.

Todas herdam de AcademiaErro, então a camada web trata qualquer erro de
regra de negócio com um único `except AcademiaErro`.
"""


class AcademiaErro(Exception):
    """Erro base do sistema."""


class ValidacaoErro(AcademiaErro):
    """Dado inválido (nome curto, e-mail errado, preço negativo...)."""


class PermissaoNegadaErro(AcademiaErro):
    """O usuário não pode executar essa ação."""


class NaoEncontradoErro(AcademiaErro):
    """Registro não existe no banco."""


class AutenticacaoErro(AcademiaErro):
    """E-mail ou senha incorretos."""


class MatriculaErro(AcademiaErro):
    """Problema com a matrícula (já ativa, vencida, sem plano...)."""


class CheckinErro(AcademiaErro):
    """Check-in não permitido (sem matrícula, academia fechada, já feito hoje)."""
