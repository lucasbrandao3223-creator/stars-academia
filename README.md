# STARS Academia — Sistema de Gestão de Academia

![Logo STARS](static/img/logo-stars.svg)

Projeto Integrado **DWS + POO + BD** — 2º ano do Técnico em Informática.

Sistema web completo de academia: **planos e matrículas**, **check-in dos alunos**, **frequência** e
**montagem de treino pelo personal trainer**, com painel de gestão para a administração.

---

## Como rodar (Windows)

1. Instale o **Python** em python.org/downloads (na instalação marque **"Add python.exe to PATH"**).
2. Descompacte o projeto e entre na pasta `academia` (a que tem o arquivo `app.py`).
3. Clique na barra de endereço da pasta, apague o texto, digite `cmd` e aperte **Enter**.
4. Na janela preta, rode (só na primeira vez):
   ```
   pip install -r requirements.txt
   ```
5. Ligue o site:
   ```
   python app.py
   ```
6. Abra no navegador: **http://127.0.0.1:5000**

A janela preta precisa ficar aberta enquanto usa o site (Ctrl + C desliga).
Na primeira execução o banco `database/academia.db` é criado sozinho com dados de exemplo.

- Recriar o banco de exemplo do zero: `python init_db.py`
- Rodar os testes automatizados: `python -m unittest -v`

### Contas de demonstração (senha de todas: `123456`)

| Perfil | E-mail | O que pode fazer |
|---|---|---|
| Aluno | aluno@teste.com | Ver plano, fazer check-in, ver frequência e treinos |
| Personal | personal@stars.com | Ver alunos, montar/editar treinos, cadastrar exercícios |
| Administrador | admin@stars.com | Painel, matrículas, planos, personais, dados da academia |

---

## Funcionalidades

**Site público** — apresentação da academia com contadores animados, planos (preço mensal ou total), áreas da academia,
calculadora de IMC interativa, perguntas frequentes, horários e contato.

**Personal trainers** (página própria) — 8 personais com filtro por especialidade e perfil completo em janela;
o aluno escolhe com qual personal quer treinar.

**Aluno**
- Cadastro e assinatura de plano (escolhe Pix, cartão ou pagamento na recepção)
- Renovação liberada nos últimos 15 dias do plano — a nova matrícula começa no dia seguinte ao fim da atual
- **Check-in** pelo site: só com plano válido, dentro do horário de funcionamento e 1 vez por dia
- **Meta da semana**: anel de progresso e meta ajustável (1 a 7 treinos), salva no banco
- **Frequência interativa**: calendário clicável (mostra horário do check-in e o treino feito no dia), troca de mês
  sem recarregar a página, sequência de dias e gráfico de evolução das últimas 8 semanas
- **Modo treino**: marca cada série, cronômetro de descanso automático com aviso sonoro, instruções de cada
  exercício, progresso salvo mesmo se recarregar a página e botão **Finalizar treino** (registra no histórico e faz o
  check-in automático)
- **Histórico** dos últimos treinos e sugestão do treino do dia (A → B → C)

**Personal trainer**
- Lista de alunos com filtros (meus alunos, sem plano, ativos sem treino)
- Ficha do aluno: matrícula, frequência, últimos check-ins e treinos
- **Montar treino**: adiciona, remove e reordena exercícios; editar e arquivar treinos
- Biblioteca de exercícios por grupo muscular (exercício em uso não pode ser excluído)

**Administrador**
- Painel: alunos ativos, check-ins do dia, matrículas vencendo, faturamento do mês, gráficos de check-ins
  (14 dias), horários de pico, faturamento por mês e alunos por plano
- Matrículas: filtro por situação (ativas, vencendo, agendadas, vencidas, canceladas), matricular/renovar na
  ficha do aluno, cancelar
- Cadastro de planos e de personais (com CREF e senha de acesso)
- Dados da academia e horário de funcionamento por dia da semana

---

## Onde está cada disciplina

### BD — Banco de Dados (`database/` e `docs/`)

- `docs/DER.png` — **Diagrama Entidade-Relacionamento**
- `database/schema.sql` — banco usado pelo sistema (SQLite)
- `database/schema_mysql.sql` — **mesmo modelo em MySQL** (Workbench/phpMyAdmin), com consultas de exemplo
- **13 tabelas** normalizadas com chave primária, estrangeira, `UNIQUE`, `CHECK`, `ON DELETE CASCADE / SET NULL` e índices
- **Generalização/especialização**: `usuario` → `aluno` e `personal` (relacionamentos 1:1)
- **N:N com atributos**: `treino_exercicio` (séries, repetições, carga, descanso e ordem)
- **3 triggers**: impedir matrículas com períodos sobrepostos; recusar check-in sem matrícula válida; impedir
  registrar treino realizado de outro aluno
- **3 views**: `vw_matriculas_situacao` (situação e dias restantes calculados), `vw_frequencia_alunos`,
  `vw_faturamento_mensal`
- Consultas com `JOIN`, `LEFT JOIN`, `GROUP BY`, `CASE WHEN`, subconsultas e `NOT EXISTS`
  (em `repositories/matricula_repo.py`)

### POO — Programação Orientada a Objetos em Python (`models/`, `repositories/`, `services/`)

| Conceito | Onde |
|---|---|
| **Classe abstrata** | `Entidade`, `Usuario` e `RepositorioBase` (`ABC` + `@abstractmethod`) |
| **Herança** | `Aluno`, `Personal` e `Administrador` herdam de `Usuario`; todos os models de `Entidade`; 8 repositórios de `RepositorioBase` |
| **Polimorfismo** | `pagina_inicial()`, `pode_ver_aluno()` e `pode_montar_treino()` respondem diferente em cada tipo de usuário. Ex.: depois do login, `redirect(url_for(usuario.pagina_inicial()))` manda cada um para a sua área sem `if` |
| **Encapsulamento** | atributos protegidos (`_nome`, `_preco`, `_series`...) com `@property` e validação nos *setters*; senha guardada só como hash |
| **Composição** | `Treino` contém `ItemTreino`; `Academia` contém `HorarioFuncionamento` |
| **Enum** | `SituacaoMatricula` (ativa, agendada, vencida, cancelada) e `FormaPagamento` |
| **Métodos de classe / fábrica** | `Matricula.nova()` calcula o fim e o valor a partir do plano; `Usuario.criar()` (*Factory Method*) |
| **Exceções personalizadas** | `exceptions.py` (`MatriculaErro`, `CheckinErro`, `PermissaoNegadaErro`...) |
| **Camadas** | *Repository/DAO* (SQL), *Service* (regras de negócio), injeção do relógio para testes |
| **Testes** | `tests/test_sistema.py` — 34 testes com `unittest` |

```
Navegador ──► app.py (rotas Flask) ──► services/ (regras) ──► repositories/ (SQL) ──► SQLite
                     │                        │
               templates/ + static/      models/ (objetos)
```

### DWS — Desenvolvimento de Web Sites (`app.py`, `templates/`, `static/`)

- Back-end **Flask**: rotas GET/POST, login com sessão, 3 níveis de acesso (decorators), mensagens *flash*, páginas de erro 404/403
- Templates **Jinja2** com herança (`base.html` → páginas; `equipe/_layout.html` → área da equipe), *macros*, filtros próprios
- **HTML5 semântico**, formulários com validação no navegador e no servidor
- **CSS próprio** (sem framework): variáveis, Grid, Flexbox e **layout responsivo** (menu no celular, tabelas que viram cartões)
- **JavaScript**: `fetch()` com JSON (calendário, meta, finalizar treino), modo treino com cronômetro e som (Web Audio),
  `localStorage`, janelas `<dialog>`, filtros, calculadora de IMC, contadores animados, montagem dinâmica do treino

---

## Estrutura de pastas

```
academia/
├── app.py                 # rotas do site (Flask)
├── config.py              # configurações e regras (dias para renovar, alerta de vencimento)
├── exceptions.py          # exceções do sistema
├── utils.py               # datas, moeda, telefone
├── init_db.py             # recria o banco com dados de exemplo
├── requirements.txt
├── database/              # schema.sql, schema_mysql.sql, conexão e dados de exemplo
├── docs/                  # DER.png (diagrama do banco) e der.dot (fonte do diagrama)
├── models/                # classes de domínio (POO)
├── repositories/          # acesso ao banco (DAO)
├── services/              # regras de negócio
├── templates/             # páginas HTML (Jinja2): público, aluno/, equipe/, admin/
├── static/                # css, js e imagens
└── tests/                 # testes automatizados
```
