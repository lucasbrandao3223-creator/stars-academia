"""Testes automatizados das regras de negócio da academia.

Executar na pasta do projeto:   python -m unittest -v
"""
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conexao import BancoDeDados  # noqa: E402
from exceptions import CheckinErro, MatriculaErro, PermissaoNegadaErro, ValidacaoErro  # noqa: E402
from academia import Academia, HorarioFuncionamento  # noqa: E402
from matricula import Matricula, SituacaoMatricula  # noqa: E402
from plano import Plano  # noqa: E402
from treino import Exercicio, ItemTreino, Treino  # noqa: E402
from usuario import Administrador, Aluno, Personal, Usuario  # noqa: E402
from academia_repo import AcademiaRepositorio  # noqa: E402
from matricula_repo import MatriculaRepositorio  # noqa: E402
from plano_repo import PlanoRepositorio  # noqa: E402
from treino_repo import ExercicioRepositorio  # noqa: E402
from usuario_repo import UsuarioRepositorio  # noqa: E402
from auth_service import AuthService  # noqa: E402
from checkin_service import CheckinService  # noqa: E402
from gestao_service import GestaoService  # noqa: E402
from matricula_service import MatriculaService  # noqa: E402
from treino_service import TreinoService  # noqa: E402
from utils import somar_meses  # noqa: E402


class TesteModels(unittest.TestCase):
    """Testes das classes, sem banco de dados."""

    def test_usuario_e_abstrato_e_factory(self):
        with self.assertRaises(TypeError):
            Usuario(nome="Ana Maria", email="a@a.com")
        self.assertIsInstance(Usuario.criar("aluno", nome="Ana Maria", email="a@a.com"), Aluno)
        self.assertIsInstance(Usuario.criar("personal", nome="Ana Maria", email="a@a.com", cref="1234-G/SP"), Personal)
        self.assertIsInstance(Usuario.criar("admin", nome="Ana Maria", email="a@a.com"), Administrador)

    def test_validacoes_do_aluno(self):
        with self.assertRaises(ValidacaoErro):
            Aluno(nome="Jo", email="jo@t.com")
        with self.assertRaises(ValidacaoErro):
            Aluno(nome="João", email="sem-arroba")
        with self.assertRaises(ValidacaoErro):
            Aluno(nome="João", email="j@t.com", objetivo="Virar astronauta")
        with self.assertRaises(ValidacaoErro):
            Aluno(nome="João", email="j@t.com", data_nascimento=date.today())   # idade 0

    def test_senha_hash(self):
        a = Aluno(nome="João Silva", email="j@t.com")
        a.definir_senha("segredo1")
        self.assertNotEqual(a.senha_hash, "segredo1")
        self.assertTrue(a.verificar_senha("segredo1"))
        self.assertFalse(a.verificar_senha("outra"))

    def test_polimorfismo_permissoes(self):
        aluno = Aluno(nome="Aluno Um", email="a1@t.com", id=1)
        personal = Personal(nome="Personal Um", email="p@t.com", cref="1234-G/SP", id=2)
        admin = Administrador(nome="Dono Um", email="d@t.com", id=3)
        self.assertTrue(aluno.pode_ver_aluno(1))
        self.assertFalse(aluno.pode_ver_aluno(99))
        self.assertTrue(personal.pode_ver_aluno(99))
        self.assertTrue(admin.pode_ver_aluno(99))
        self.assertFalse(aluno.pode_montar_treino())
        self.assertTrue(personal.pode_montar_treino())
        self.assertFalse(admin.pode_montar_treino())
        personal.ativo = False
        self.assertFalse(personal.pode_montar_treino())
        self.assertEqual([u.pagina_inicial() for u in (aluno, personal, admin)],
                         ["aluno_painel", "equipe_alunos", "admin_dashboard"])

    def test_plano_calcula_total_e_economia(self):
        mensal = Plano(nome="Mensal", duracao_meses=1, preco_mensal=120)
        anual = Plano(nome="Anual", duracao_meses=12, preco_mensal="90,00")
        self.assertEqual(anual.valor_total, 1080)
        self.assertEqual(anual.economia_sobre(mensal.preco_mensal), 25)
        with self.assertRaises(ValidacaoErro):
            Plano(nome="Errado", duracao_meses=0, preco_mensal=10)

    def test_matricula_periodo_e_situacao(self):
        plano = Plano(nome="Trimestral", duracao_meses=3, preco_mensal=100, id=1)
        m = Matricula.nova(1, plano, date(2026, 1, 31), "pix")
        self.assertEqual(m.data_fim, date(2026, 4, 29))       # 31/01 + 3 meses - 1 dia
        self.assertEqual(m.valor_total, 300)
        self.assertEqual(m.situacao(date(2026, 1, 1)), SituacaoMatricula.AGENDADA)
        self.assertEqual(m.situacao(date(2026, 2, 15)), SituacaoMatricula.ATIVA)
        self.assertEqual(m.situacao(date(2026, 5, 1)), SituacaoMatricula.VENCIDA)
        m.cancelar()
        self.assertEqual(m.situacao(date(2026, 2, 15)), SituacaoMatricula.CANCELADA)
        with self.assertRaises(MatriculaErro):
            m.cancelar()

    def test_somar_meses_fim_de_mes(self):
        self.assertEqual(somar_meses(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(somar_meses(date(2026, 11, 15), 3), date(2027, 2, 15))

    def test_treino_e_itens(self):
        t = Treino(aluno_id=1, personal_id=2, nome="Treino B - Costas e Bíceps")
        with self.assertRaises(ValidacaoErro):
            t.validar()                                   # sem exercícios
        t.adicionar_item(ItemTreino(exercicio_id=1, series=4, repeticoes="10-12", carga_kg="22,5", descanso_seg=90))
        t.adicionar_item(ItemTreino(exercicio_id=2, series=3, repeticoes="12"))
        self.assertEqual([i.ordem for i in t.itens], [1, 2])
        self.assertEqual(t.total_series, 7)
        self.assertEqual(t.letra, "B")
        self.assertEqual(t.itens[0].carga_texto, "22,5 kg")
        self.assertEqual(t.itens[0].descanso_texto, "1min30")
        with self.assertRaises(ValidacaoErro):
            ItemTreino(exercicio_id=1, series=0, repeticoes="10")
        with self.assertRaises(ValidacaoErro):
            ItemTreino(exercicio_id=1, series=3, repeticoes="")

    def test_academia_aberta(self):
        a = Academia(nome="Academia Teste")
        a.definir_horario(HorarioFuncionamento(0, "06:00", "22:00"))
        segunda = datetime(2026, 11, 9, 7, 0)            # 09/11/2026 é segunda-feira
        self.assertTrue(a.esta_aberta(segunda))
        self.assertFalse(a.esta_aberta(segunda.replace(hour=23)))
        self.assertFalse(a.esta_aberta(segunda + timedelta(days=1)))


class TesteComBanco(unittest.TestCase):
    """Banco temporário com academia aberta todo dia das 6h às 22h."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        banco = BancoDeDados(os.path.join(self.pasta.name, "teste.db"))
        banco.criar_estrutura()
        self.conn = banco.conectar()
        self.agora = datetime(2026, 11, 9, 18, 30)       # segunda-feira, 18h30
        relogio = lambda: self.agora  # noqa: E731

        academia = Academia(nome="Academia Teste")
        for d in range(7):
            academia.definir_horario(HorarioFuncionamento(d, "06:00", "22:00"))
        AcademiaRepositorio(self.conn).salvar(academia)

        usuarios = UsuarioRepositorio(self.conn)
        self.admin = Administrador(nome="Dono Teste", email="admin@t.com")
        self.admin.definir_senha("123456")
        usuarios.salvar(self.admin)
        self.personal = Personal(nome="Carla Personal", email="p@t.com", cref="1234-G/SP")
        self.personal.definir_senha("123456")
        usuarios.salvar(self.personal)
        self.aluno = Aluno(nome="Aluno Um", email="a1@t.com", personal_id=self.personal.id)
        self.aluno.definir_senha("123456")
        usuarios.salvar(self.aluno)
        self.aluno2 = Aluno(nome="Aluno Dois", email="a2@t.com")
        self.aluno2.definir_senha("123456")
        usuarios.salvar(self.aluno2)

        planos = PlanoRepositorio(self.conn)
        self.mensal = planos.salvar(Plano(nome="Mensal", duracao_meses=1, preco_mensal=120))
        self.anual = planos.salvar(Plano(nome="Anual", duracao_meses=12, preco_mensal=90))

        self.conn.execute("INSERT INTO grupo_muscular (nome) VALUES ('Peito'), ('Costas')")
        self.conn.commit()
        exercicios = ExercicioRepositorio(self.conn)
        self.supino = exercicios.salvar(Exercicio(nome="Supino reto", grupo_muscular_id=1))
        self.remada = exercicios.salvar(Exercicio(nome="Remada curvada", grupo_muscular_id=2))

        self.matriculas = MatriculaService(self.conn, relogio=relogio)
        self.checkins = CheckinService(self.conn, relogio=relogio)
        self.treinos = TreinoService(self.conn)
        self.gestao = GestaoService(self.conn, relogio=relogio)

    def tearDown(self):
        self.conn.close()
        self.pasta.cleanup()

    # ---------------- matrícula ----------------
    def test_assinar_plano(self):
        m = self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        self.assertEqual(m.data_inicio, self.agora.date())
        self.assertEqual(m.data_fim, date(2026, 12, 8))
        self.assertEqual(m.valor_total, 120)

    def test_nao_assina_com_plano_ativo_longe_do_fim(self):
        self.matriculas.assinar(self.aluno, self.anual.id, "cartao")
        with self.assertRaises(MatriculaErro):
            self.matriculas.assinar(self.aluno, self.mensal.id, "pix")

    def test_renovacao_comeca_apos_o_fim(self):
        m = self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        self.agora = datetime(2026, 12, 1, 10, 0)         # faltam 7 dias
        renovada = self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        self.assertEqual(renovada.data_inicio, m.data_fim + timedelta(days=1))
        with self.assertRaises(MatriculaErro):            # não deixa agendar duas renovações
            self.matriculas.assinar(self.aluno, self.mensal.id, "pix")

    def test_trigger_impede_matriculas_sobrepostas(self):
        self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        repo = MatriculaRepositorio(self.conn)
        with self.assertRaises(ValidacaoErro):
            repo.salvar(Matricula.nova(self.aluno.id, self.anual, self.agora.date(), "pix"))

    def test_somente_admin_matricula_e_cancela(self):
        with self.assertRaises(PermissaoNegadaErro):
            self.matriculas.matricular(self.personal, self.aluno.id, self.mensal.id, "pix")
        m = self.matriculas.matricular(self.admin, self.aluno.id, self.mensal.id, "dinheiro")
        with self.assertRaises(PermissaoNegadaErro):
            self.matriculas.cancelar(self.aluno, m.id)
        self.matriculas.cancelar(self.admin, m.id)
        self.assertIsNone(MatriculaRepositorio(self.conn).vigente_do_aluno(self.aluno.id, self.agora.date()))

    def test_personal_nao_assina_plano(self):
        with self.assertRaises(PermissaoNegadaErro):
            self.matriculas.assinar(self.personal, self.mensal.id, "pix")

    # ---------------- check-in ----------------
    def test_checkin_exige_matricula(self):
        with self.assertRaises(CheckinErro):
            self.checkins.fazer_checkin(self.aluno)
        self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        c = self.checkins.fazer_checkin(self.aluno)
        self.assertEqual(c.data, self.agora.date())

    def test_um_checkin_por_dia(self):
        self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        self.checkins.fazer_checkin(self.aluno)
        with self.assertRaises(CheckinErro):
            self.checkins.fazer_checkin(self.aluno)
        self.assertTrue(self.checkins.situacao_hoje(self.aluno)["feito"])

    def test_checkin_so_com_academia_aberta(self):
        self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        self.agora = datetime(2026, 11, 9, 23, 15)
        with self.assertRaises(CheckinErro):
            self.checkins.fazer_checkin(self.aluno)

    def test_trigger_recusa_checkin_sem_matricula(self):
        """SQL direto no banco: o trigger recusa mesmo sem passar pelo Python."""
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO checkin (aluno_id, data, hora) VALUES (?, '2026-11-09', '10:00')",
                              (self.aluno.id,))
            self.conn.commit()

    def test_trigger_recusa_checkin_sem_matricula_via_repositorio(self):
        from matricula import Checkin
        from matricula_repo import CheckinRepositorio
        with self.assertRaises(ValidacaoErro):
            CheckinRepositorio(self.conn).salvar(Checkin(self.aluno.id, "2026-11-09", "10:00"))

    def test_frequencia_e_sequencia(self):
        self.matriculas.matricular(self.admin, self.aluno.id, self.mensal.id, "pix",
                                   data_inicio=date(2026, 11, 1))
        from matricula import Checkin
        from matricula_repo import CheckinRepositorio
        repo = CheckinRepositorio(self.conn)
        for dia in (5, 7, 8, 9):
            repo.salvar(Checkin(self.aluno.id, date(2026, 11, dia), "18:00"))
        f = self.checkins.frequencia(self.aluno.id)
        self.assertEqual(f["no_mes"], 4)
        self.assertEqual(f["sequencia"], 3)                # dias 7, 8 e 9 seguidos

    # ---------------- treinos ----------------
    def linhas(self):
        return [{"exercicio_id": self.supino.id, "series": 4, "repeticoes": "10", "carga_kg": "30",
                 "descanso_seg": 90, "observacao": ""},
                {"exercicio_id": "", "series": 3, "repeticoes": "12", "carga_kg": "", "descanso_seg": 60,
                 "observacao": ""},                         # linha vazia é ignorada
                {"exercicio_id": self.remada.id, "series": 3, "repeticoes": "12", "carga_kg": "",
                 "descanso_seg": 60, "observacao": "pegada pronada"}]

    def test_personal_monta_treino(self):
        t = self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A - Peito e Costas", "", self.linhas())
        salvo = self.treinos.treinos_do_aluno(self.aluno, self.aluno.id)[0]
        self.assertEqual(salvo.id, t.id)
        self.assertEqual([i.exercicio_nome for i in salvo.itens], ["Supino reto", "Remada curvada"])
        self.assertEqual(salvo.itens[0].carga_kg, 30)

    def test_aluno_e_admin_nao_montam_treino(self):
        for usuario in (self.aluno, self.admin):
            with self.assertRaises(PermissaoNegadaErro):
                self.treinos.salvar_treino(usuario, self.aluno.id, "Treino A", "", self.linhas())

    def test_aluno_nao_ve_treino_de_outro(self):
        self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A", "", self.linhas())
        with self.assertRaises(PermissaoNegadaErro):
            self.treinos.treinos_do_aluno(self.aluno2, self.aluno.id)

    def test_editar_e_arquivar_treino(self):
        t = self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A", "", self.linhas())
        self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A - Só peito", "",
                                   self.linhas()[:1], treino_id=t.id)
        editado = self.treinos.treinos.obter(t.id)
        self.assertEqual((editado.nome, len(editado.itens)), ("Treino A - Só peito", 1))
        self.treinos.alternar_treino(self.personal, t.id)
        self.assertEqual(self.treinos.treinos_do_aluno(self.aluno, self.aluno.id), [])

    def test_treino_sem_exercicio_e_recusado(self):
        with self.assertRaises(ValidacaoErro):
            self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino vazio", "", [])

    def test_exercicio_em_uso_nao_pode_ser_excluido(self):
        self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A", "", self.linhas())
        with self.assertRaises(ValidacaoErro):
            self.gestao.excluir_exercicio(self.personal, self.supino.id)

    def test_concluir_treino_e_checkin_automatico(self):
        self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        t = self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A", "", self.linhas())
        servico = TreinoService(self.conn, relogio=lambda: self.agora)
        realizado, auto = servico.concluir_treino(self.aluno, t.id, 5, 48)
        self.assertEqual((realizado.series_feitas, realizado.series_total, auto), (5, 7, True))
        with self.assertRaises(ValidacaoErro):           # só uma vez por dia
            servico.concluir_treino(self.aluno, t.id, 7, 50)
        with self.assertRaises(PermissaoNegadaErro):     # treino de outro aluno
            servico.concluir_treino(self.aluno2, t.id, 3, 20)
        painel = servico.painel_do_aluno(self.aluno)
        self.assertTrue(painel["treinos"][0].feito_hoje)
        f = self.checkins.frequencia(self.aluno.id)
        hoje = [d for s in f["semanas"] for d in s if d["hoje"]][0]
        self.assertEqual(hoje["treinos"][0]["series_feitas"], 5)

    def test_concluir_treino_exige_plano_e_series(self):
        t = self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A", "", self.linhas())
        servico = TreinoService(self.conn, relogio=lambda: self.agora)
        with self.assertRaises(ValidacaoErro):           # sem plano ativo
            servico.concluir_treino(self.aluno, t.id, 3, 30)
        self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        with self.assertRaises(ValidacaoErro):           # mais séries do que o treino tem
            servico.concluir_treino(self.aluno, t.id, 99, 30)

    def test_trigger_treino_realizado_de_outro_aluno(self):
        import sqlite3
        t = self.treinos.salvar_treino(self.personal, self.aluno.id, "Treino A", "", self.linhas())
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO treino_realizado (aluno_id, treino_id, data, series_feitas, series_total, "
                              "duracao_min) VALUES (?, ?, '2026-11-09', 3, 7, 30)", (self.aluno2.id, t.id))

    def test_meta_semanal_e_escolher_personal(self):
        self.gestao.definir_meta(self.aluno2, 5)
        self.assertEqual(UsuarioRepositorio(self.conn).obter(self.aluno2.id).meta_semanal, 5)
        with self.assertRaises(ValidacaoErro):
            self.gestao.definir_meta(self.aluno2, 8)
        self.gestao.escolher_personal(self.aluno2, self.personal.id)
        self.assertEqual(UsuarioRepositorio(self.conn).obter(self.aluno2.id).personal_id, self.personal.id)
        with self.assertRaises(PermissaoNegadaErro):
            self.gestao.escolher_personal(self.personal, self.personal.id)

    # ---------------- gestão e cadastro ----------------
    def test_lista_de_alunos_da_equipe(self):
        self.matriculas.assinar(self.aluno, self.mensal.id, "pix")
        ativos = self.gestao.alunos(self.personal, situacao="ativos")
        self.assertEqual([a.nome for a in ativos], ["Aluno Um"])
        meus = self.gestao.alunos(self.personal, somente_meus=True)
        self.assertEqual([a.nome for a in meus], ["Aluno Um"])
        with self.assertRaises(PermissaoNegadaErro):
            self.gestao.alunos(self.aluno)

    def test_admin_cadastra_personal(self):
        p = self.gestao.salvar_personal(self.admin, {"nome": "Novo Personal", "email": "novo@t.com",
                                                     "telefone": "", "cref": "9999-G/SP", "senha": "abcdef"})
        self.assertIsInstance(UsuarioRepositorio(self.conn).obter(p.id), Personal)
        with self.assertRaises(ValidacaoErro):           # CREF repetido
            self.gestao.salvar_personal(self.admin, {"nome": "Outro Personal", "email": "outro@t.com",
                                                     "telefone": "", "cref": "9999-G/SP", "senha": "abcdef"})
        self.assertIsNone(UsuarioRepositorio(self.conn).buscar_por_email("outro@t.com"))  # transação desfeita

    def test_cadastro_e_login_do_aluno(self):
        auth = AuthService(self.conn)
        auth.cadastrar_aluno("Maria Nova", "maria@t.com", "11999998888", "abcdef", "abcdef", "2000-05-10", "Força")
        usuario = auth.autenticar("MARIA@t.com", "abcdef")
        self.assertIsInstance(usuario, Aluno)
        self.assertEqual(usuario.objetivo, "Força")
        with self.assertRaises(ValidacaoErro):
            auth.cadastrar_aluno("Maria Nova", "maria@t.com", "", "abcdef", "abcdef")


if __name__ == "__main__":
    unittest.main()
