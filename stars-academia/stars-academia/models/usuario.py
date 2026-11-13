"""Usuários: classe abstrata Usuario e as filhas Aluno, Personal e Administrador."""
import re
from abc import abstractmethod

from werkzeug.security import check_password_hash, generate_password_hash

from exceptions import ValidacaoErro
from models.entidade import Entidade
from utils import apenas_digitos, calcular_idade, formatar_telefone, para_data

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Usuario(Entidade):
    """Classe abstrata com o que todo usuário tem em comum.

    - Herança: Aluno, Personal e Administrador herdam daqui.
    - Polimorfismo: cada filha responde do seu jeito a pagina_inicial(),
      pode_ver_aluno() e pode_montar_treino().
    - Encapsulamento: a senha nunca fica em texto puro, só o hash.
    """

    TIPO = None
    ROTULO = "Usuário"

    def __init__(self, nome, email, telefone="", senha_hash=None, id=None, criado_em=None):
        super().__init__(id)
        self.nome = nome
        self.email = email
        self.telefone = telefone
        self._senha_hash = senha_hash
        self.criado_em = criado_em

    # ---------------- propriedades com validação ----------------
    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valor):
        valor = (valor or "").strip()
        if len(valor) < 3:
            raise ValidacaoErro("O nome precisa ter pelo menos 3 letras.")
        self._nome = valor

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valor):
        valor = (valor or "").strip().lower()
        if not EMAIL_REGEX.match(valor):
            raise ValidacaoErro("Informe um e-mail válido.")
        self._email = valor

    @property
    def telefone(self):
        return self._telefone

    @telefone.setter
    def telefone(self, valor):
        digitos = apenas_digitos(valor)
        if digitos and len(digitos) not in (10, 11):
            raise ValidacaoErro("O telefone deve ter DDD + número (10 ou 11 dígitos).")
        self._telefone = digitos

    @property
    def telefone_formatado(self):
        return formatar_telefone(self._telefone)

    @property
    def senha_hash(self):
        return self._senha_hash

    @property
    def primeiro_nome(self):
        return self._nome.split()[0]

    @property
    def iniciais(self):
        partes = self._nome.split()
        return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()

    @property
    def tipo(self):
        return self.TIPO

    # ---------------- senha ----------------
    def definir_senha(self, senha):
        if not senha or len(senha) < 6:
            raise ValidacaoErro("A senha precisa ter pelo menos 6 caracteres.")
        self._senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return bool(self._senha_hash) and check_password_hash(self._senha_hash, senha or "")

    def validar(self):
        if not self._senha_hash:
            raise ValidacaoErro("Defina uma senha para o usuário.")

    # ---------------- comportamento polimórfico ----------------
    @abstractmethod
    def pagina_inicial(self):
        """Nome da rota para onde o usuário vai depois do login."""

    @abstractmethod
    def pode_ver_aluno(self, aluno_id):
        """Se pode ver a ficha (matrícula, frequência e treinos) de um aluno."""

    def pode_montar_treino(self):
        return False

    @property
    def faz_parte_da_equipe(self):
        return False

    @property
    def eh_admin(self):
        return False

    # ---------------- fábrica ----------------
    @staticmethod
    def criar(tipo, **dados):
        """Factory Method: devolve a subclasse certa a partir do tipo gravado no banco."""
        classes = {Aluno.TIPO: Aluno, Personal.TIPO: Personal, Administrador.TIPO: Administrador}
        if tipo not in classes:
            raise ValidacaoErro(f"Tipo de usuário desconhecido: {tipo}")
        return classes[tipo](**dados)


class Aluno(Usuario):
    """Pessoa matriculada na academia."""

    TIPO = "aluno"
    ROTULO = "Aluno"
    OBJETIVOS = ("Hipertrofia", "Emagrecimento", "Condicionamento físico", "Força", "Saúde e bem-estar")

    def __init__(self, nome, email, telefone="", senha_hash=None, id=None, criado_em=None,
                 data_nascimento=None, objetivo="", personal_id=None, personal_nome=None, meta_semanal=3):
        super().__init__(nome, email, telefone, senha_hash, id, criado_em)
        self.data_nascimento = data_nascimento
        self.objetivo = objetivo
        self.meta_semanal = meta_semanal
        self.personal_id = personal_id
        self.personal_nome = personal_nome

    @property
    def data_nascimento(self):
        return self._nascimento

    @data_nascimento.setter
    def data_nascimento(self, valor):
        if not valor:
            self._nascimento = None
            return
        try:
            data = para_data(valor)
        except ValueError:
            raise ValidacaoErro("Data de nascimento inválida.")
        idade = calcular_idade(data)
        if idade is None or not 10 <= idade <= 100:
            raise ValidacaoErro("Confira a data de nascimento (idade entre 10 e 100 anos).")
        self._nascimento = data

    @property
    def objetivo(self):
        return self._objetivo

    @objetivo.setter
    def objetivo(self, valor):
        valor = (valor or "").strip()
        if valor and valor not in self.OBJETIVOS:
            raise ValidacaoErro("Escolha um objetivo da lista.")
        self._objetivo = valor

    @property
    def meta_semanal(self):
        return self._meta

    @meta_semanal.setter
    def meta_semanal(self, valor):
        try:
            valor = int(valor if valor not in (None, "") else 3)
        except (TypeError, ValueError):
            raise ValidacaoErro("Meta semanal inválida.")
        if not 1 <= valor <= 7:
            raise ValidacaoErro("A meta deve ser de 1 a 7 treinos por semana.")
        self._meta = valor

    def idade(self, hoje=None):
        return calcular_idade(self._nascimento, hoje)

    def pagina_inicial(self):
        return "aluno_painel"

    def pode_ver_aluno(self, aluno_id):
        return int(aluno_id) == self.id     # o aluno só vê a própria ficha



class Personal(Usuario):
    """Personal trainer: acompanha alunos e monta os treinos."""

    TIPO = "personal"
    ROTULO = "Personal trainer"

    def __init__(self, nome, email, telefone="", senha_hash=None, id=None, criado_em=None,
                 cref="", especialidade="", bio="", ativo=True, total_alunos=0, anos_experiencia=None,
                 total_treinos=0):
        super().__init__(nome, email, telefone, senha_hash, id, criado_em)
        self.cref = cref
        self.especialidade = especialidade or ""
        self.bio = bio or ""
        self.anos_experiencia = anos_experiencia
        self.total_treinos = total_treinos or 0
        self.ativo = bool(ativo)
        self.total_alunos = total_alunos or 0

    @property
    def cref(self):
        return self._cref

    @cref.setter
    def cref(self, valor):
        valor = (valor or "").strip().upper()
        if len(valor) < 4:
            raise ValidacaoErro("Informe o CREF do personal (ex.: 123456-G/SP).")
        self._cref = valor

    @property
    def anos_experiencia(self):
        return self._anos

    @anos_experiencia.setter
    def anos_experiencia(self, valor):
        if valor in (None, ""):
            self._anos = None
            return
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            raise ValidacaoErro("Anos de experiência inválido.")
        if not 0 <= valor <= 60:
            raise ValidacaoErro("Anos de experiência deve ficar entre 0 e 60.")
        self._anos = valor

    @property
    def tags(self):
        """Especialidades separadas (ex.: 'Hipertrofia e força' -> ['Hipertrofia', 'Força'])."""
        texto = self.especialidade.replace(" e ", ",").replace("/", ",")
        return [t.strip().capitalize() for t in texto.split(",") if t.strip()]

    def pagina_inicial(self):
        return "equipe_alunos"

    def pode_ver_aluno(self, aluno_id):
        return True

    def pode_montar_treino(self):
        return self.ativo

    @property
    def faz_parte_da_equipe(self):
        return True



class Administrador(Usuario):
    """Dono / recepção da academia: cuida de planos, matrículas e equipe."""

    TIPO = "admin"
    ROTULO = "Administrador"

    def pagina_inicial(self):
        return "admin_dashboard"

    def pode_ver_aluno(self, aluno_id):
        return True

    @property
    def faz_parte_da_equipe(self):
        return True

    @property
    def eh_admin(self):
        return True
