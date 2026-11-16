import sqlite3

from exceptions import ValidacaoErro
from usuario import Usuario
from base import RepositorioBase


class UsuarioRepositorio(RepositorioBase):
    """Lê e grava usuários. A tabela usuario guarda o comum; aluno e personal guardam o específico."""

    TABELA = "usuario"
    NOME_ENTIDADE = "Usuário"

    SQL_BASE = """
        SELECT u.*,
               a.data_nascimento, a.objetivo, a.meta_semanal, a.personal_id, pu.nome AS personal_nome,
               p.cref, p.especialidade, p.bio, p.anos_experiencia, p.ativo AS personal_ativo,
               (SELECT COUNT(*) FROM aluno x WHERE x.personal_id = u.id) AS total_alunos,
               (SELECT COUNT(*) FROM treino t WHERE t.personal_id = u.id AND t.ativo = 1) AS total_treinos
          FROM usuario u
          LEFT JOIN aluno a     ON a.usuario_id = u.id
          LEFT JOIN usuario pu  ON pu.id = a.personal_id
          LEFT JOIN personal p  ON p.usuario_id = u.id"""

    def _para_objeto(self, linha):
        dados = {k: linha[k] for k in ("id", "nome", "email", "telefone", "senha_hash", "criado_em")}
        if linha["tipo"] == "aluno":
            dados.update(data_nascimento=linha["data_nascimento"], objetivo=linha["objetivo"],
                         meta_semanal=linha["meta_semanal"], personal_id=linha["personal_id"],
                         personal_nome=linha["personal_nome"])
        elif linha["tipo"] == "personal":
            dados.update(cref=linha["cref"], especialidade=linha["especialidade"], bio=linha["bio"],
                         anos_experiencia=linha["anos_experiencia"], ativo=linha["personal_ativo"],
                         total_alunos=linha["total_alunos"], total_treinos=linha["total_treinos"])
        return Usuario.criar(linha["tipo"], **dados)

    def buscar_por_id(self, id):
        linha = self._consultar_um(self.SQL_BASE + " WHERE u.id = ?", (id,))
        return self._para_objeto(linha) if linha else None

    def buscar_por_email(self, email):
        linha = self._consultar_um(self.SQL_BASE + " WHERE u.email = ?", ((email or "").strip().lower(),))
        return self._para_objeto(linha) if linha else None

    def email_existe(self, email):
        return self.buscar_por_email(email) is not None

    def listar_alunos(self, busca=None, personal_id=None):
        sql = self.SQL_BASE + " WHERE u.tipo = 'aluno'"
        parametros = []
        if busca:
            sql += " AND (u.nome LIKE ? OR u.email LIKE ? OR u.telefone LIKE ?)"
            termo = f"%{busca.strip()}%"
            parametros += [termo, termo, termo]
        if personal_id:
            sql += " AND a.personal_id = ?"
            parametros.append(int(personal_id))
        return self._lista(self._consultar(sql + " ORDER BY u.nome", parametros))

    def listar_personais(self, apenas_ativos=True):
        sql = self.SQL_BASE + " WHERE u.tipo = 'personal'"
        if apenas_ativos:
            sql += " AND p.ativo = 1"
        return self._lista(self._consultar(sql + " ORDER BY p.ativo DESC, u.nome"))

    def salvar(self, usuario):
        """Grava o usuário. Aluno e personal também gravam a tabela própria deles.

        Tudo fica numa transação: se der erro no meio (ex.: CREF repetido), nada é gravado.
        """
        usuario.validar()
        try:
            # 1) tabela usuario (dados comuns a todos)
            if usuario.eh_novo:
                cursor = self._conn.execute(
                    "INSERT INTO usuario (nome, email, telefone, senha_hash, tipo) VALUES (?, ?, ?, ?, ?)",
                    (usuario.nome, usuario.email, usuario.telefone, usuario.senha_hash, usuario.tipo))
                usuario_id = cursor.lastrowid
            else:
                usuario_id = usuario.id
                self._conn.execute(
                    "UPDATE usuario SET nome = ?, email = ?, telefone = ?, senha_hash = ? WHERE id = ?",
                    (usuario.nome, usuario.email, usuario.telefone, usuario.senha_hash, usuario.id))

            # 2) tabela de especialização (aluno ou personal)
            if usuario.tipo == "aluno":
                self._salvar_aluno(usuario_id, usuario)
            elif usuario.tipo == "personal":
                self._salvar_personal(usuario_id, usuario)

            self._conn.commit()
        except sqlite3.IntegrityError as erro:
            self._conn.rollback()
            raise ValidacaoErro(self._traduzir_erro(erro)) from erro

        if usuario.eh_novo:
            usuario.id = usuario_id
        return usuario

    def _salvar_aluno(self, usuario_id, aluno):
        nascimento = aluno.data_nascimento.isoformat() if aluno.data_nascimento else None
        dados = (nascimento, aluno.objetivo, aluno.meta_semanal, aluno.personal_id, usuario_id)
        # tenta atualizar; se a linha ainda não existe (aluno novo), insere
        cursor = self._conn.execute(
            "UPDATE aluno SET data_nascimento = ?, objetivo = ?, meta_semanal = ?, personal_id = ? "
            "WHERE usuario_id = ?", dados)
        if cursor.rowcount == 0:
            self._conn.execute(
                "INSERT INTO aluno (data_nascimento, objetivo, meta_semanal, personal_id, usuario_id) "
                "VALUES (?, ?, ?, ?, ?)", dados)

    def _salvar_personal(self, usuario_id, personal):
        dados = (personal.cref, personal.especialidade, personal.bio, personal.anos_experiencia,
                 int(personal.ativo), usuario_id)
        cursor = self._conn.execute(
            "UPDATE personal SET cref = ?, especialidade = ?, bio = ?, anos_experiencia = ?, ativo = ? "
            "WHERE usuario_id = ?", dados)
        if cursor.rowcount == 0:
            self._conn.execute(
                "INSERT INTO personal (cref, especialidade, bio, anos_experiencia, ativo, usuario_id) "
                "VALUES (?, ?, ?, ?, ?, ?)", dados)
