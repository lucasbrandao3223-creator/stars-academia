"""Cadastro de alunos e login."""
from exceptions import AutenticacaoErro, ValidacaoErro
from models.usuario import Aluno
from repositories import UsuarioRepositorio


class AuthService:

    def __init__(self, conexao):
        self.usuarios = UsuarioRepositorio(conexao)

    def cadastrar_aluno(self, nome, email, telefone, senha, confirmacao, data_nascimento=None, objetivo=""):
        aluno = Aluno(nome=nome, email=email, telefone=telefone,
                      data_nascimento=data_nascimento or None, objetivo=objetivo)
        if senha != confirmacao:
            raise ValidacaoErro("As senhas não conferem.")
        if self.usuarios.email_existe(aluno.email):
            raise ValidacaoErro("Este e-mail já está cadastrado.")
        aluno.definir_senha(senha)
        return self.usuarios.salvar(aluno)

    def autenticar(self, email, senha):
        usuario = self.usuarios.buscar_por_email(email)
        if usuario is None or not usuario.verificar_senha(senha):
            raise AutenticacaoErro("E-mail ou senha incorretos.")
        return usuario
