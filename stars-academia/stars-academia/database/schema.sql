-- =====================================================================
--  STARS ACADEMIA - Sistema de Gestão de Academia
--  Projeto Integrado DWS + POO + BD
--  Script de criação do banco de dados (SQLite)
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP VIEW    IF EXISTS vw_matriculas_situacao;
DROP VIEW    IF EXISTS vw_frequencia_alunos;
DROP VIEW    IF EXISTS vw_faturamento_mensal;
DROP TRIGGER IF EXISTS trg_matricula_sem_sobreposicao;
DROP TRIGGER IF EXISTS trg_checkin_exige_matricula;
DROP TRIGGER IF EXISTS trg_treino_realizado_do_aluno;
DROP TABLE   IF EXISTS treino_realizado;
DROP TABLE   IF EXISTS treino_exercicio;
DROP TABLE   IF EXISTS treino;
DROP TABLE   IF EXISTS exercicio;
DROP TABLE   IF EXISTS grupo_muscular;
DROP TABLE   IF EXISTS checkin;
DROP TABLE   IF EXISTS matricula;
DROP TABLE   IF EXISTS plano;
DROP TABLE   IF EXISTS aluno;
DROP TABLE   IF EXISTS personal;
DROP TABLE   IF EXISTS usuario;
DROP TABLE   IF EXISTS horario_funcionamento;
DROP TABLE   IF EXISTS academia;

-- ---------------------------------------------------------------------
-- ACADEMIA: dados da academia (tabela de linha única, id = 1)
-- ---------------------------------------------------------------------
CREATE TABLE academia (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    nome       TEXT NOT NULL,
    slogan     TEXT,
    descricao  TEXT,
    endereco   TEXT,
    cidade     TEXT,
    telefone   TEXT,
    whatsapp   TEXT,
    instagram  TEXT
);

-- dia_semana: 0 = segunda ... 6 = domingo (dia ausente = fechado)
CREATE TABLE horario_funcionamento (
    academia_id  INTEGER NOT NULL DEFAULT 1 REFERENCES academia(id) ON DELETE CASCADE,
    dia_semana   INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
    abertura     TEXT    NOT NULL,     -- 'HH:MM'
    fechamento   TEXT    NOT NULL,     -- 'HH:MM'
    PRIMARY KEY (academia_id, dia_semana),
    CHECK (abertura < fechamento)
);

-- ---------------------------------------------------------------------
-- USUARIO: dados de acesso comuns a todos (generalização)
-- tipo: aluno, personal ou admin
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    telefone    TEXT,
    senha_hash  TEXT NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('aluno', 'personal', 'admin')),
    criado_em   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- PERSONAL: especialização de usuario (1:1)
-- ---------------------------------------------------------------------
CREATE TABLE personal (
    usuario_id     INTEGER PRIMARY KEY REFERENCES usuario(id) ON DELETE CASCADE,
    cref           TEXT    NOT NULL UNIQUE,
    especialidade     TEXT,
    bio               TEXT,
    anos_experiencia  INTEGER CHECK (anos_experiencia IS NULL OR anos_experiencia BETWEEN 0 AND 60),
    ativo             INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

-- ---------------------------------------------------------------------
-- ALUNO: especialização de usuario (1:1), com personal responsável (N:1)
-- ---------------------------------------------------------------------
CREATE TABLE aluno (
    usuario_id       INTEGER PRIMARY KEY REFERENCES usuario(id) ON DELETE CASCADE,
    data_nascimento  TEXT,      -- 'AAAA-MM-DD'
    objetivo         TEXT,
    meta_semanal     INTEGER NOT NULL DEFAULT 3 CHECK (meta_semanal BETWEEN 1 AND 7),
    personal_id      INTEGER REFERENCES personal(usuario_id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- PLANO: mensal, trimestral, semestral, anual...
-- ---------------------------------------------------------------------
CREATE TABLE plano (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT    NOT NULL UNIQUE,
    descricao      TEXT,
    duracao_meses  INTEGER NOT NULL CHECK (duracao_meses BETWEEN 1 AND 24),
    preco_mensal   REAL    NOT NULL CHECK (preco_mensal > 0),
    ativo          INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

-- ---------------------------------------------------------------------
-- MATRICULA: o aluno contrata um plano por um período
-- status gravado: ativa ou cancelada (vencida é calculada pela data)
-- ---------------------------------------------------------------------
CREATE TABLE matricula (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id         INTEGER NOT NULL REFERENCES aluno(usuario_id),
    plano_id         INTEGER NOT NULL REFERENCES plano(id),
    data_inicio      TEXT    NOT NULL,
    data_fim         TEXT    NOT NULL,
    valor_total      REAL    NOT NULL CHECK (valor_total >= 0),
    forma_pagamento  TEXT    NOT NULL CHECK (forma_pagamento IN ('pix', 'cartao', 'dinheiro')),
    status           TEXT    NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'cancelada')),
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    CHECK (data_inicio <= data_fim)
);
CREATE INDEX idx_matricula_aluno ON matricula (aluno_id, data_fim);

-- ---------------------------------------------------------------------
-- CHECKIN: entrada do aluno na academia (no máximo 1 por dia)
-- ---------------------------------------------------------------------
CREATE TABLE checkin (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id  INTEGER NOT NULL REFERENCES aluno(usuario_id) ON DELETE CASCADE,
    data      TEXT    NOT NULL,   -- 'AAAA-MM-DD'
    hora      TEXT    NOT NULL,   -- 'HH:MM'
    UNIQUE (aluno_id, data)
);
CREATE INDEX idx_checkin_data ON checkin (data);

-- ---------------------------------------------------------------------
-- GRUPO_MUSCULAR e EXERCICIO: biblioteca de exercícios
-- ---------------------------------------------------------------------
CREATE TABLE grupo_muscular (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT NOT NULL UNIQUE
);

CREATE TABLE exercicio (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    nome               TEXT    NOT NULL UNIQUE,
    grupo_muscular_id  INTEGER NOT NULL REFERENCES grupo_muscular(id),
    equipamento        TEXT,
    instrucoes         TEXT
);

-- ---------------------------------------------------------------------
-- TREINO: ficha montada pelo personal para um aluno (Treino A, B, C...)
-- ---------------------------------------------------------------------
CREATE TABLE treino (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id     INTEGER NOT NULL REFERENCES aluno(usuario_id) ON DELETE CASCADE,
    personal_id  INTEGER NOT NULL REFERENCES personal(usuario_id),
    nome         TEXT    NOT NULL,
    observacoes  TEXT,
    ativo        INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_em    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    atualizado_em TEXT   NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_treino_aluno ON treino (aluno_id);

-- ---------------------------------------------------------------------
-- TREINO_EXERCICIO: N:N entre treino e exercício, com atributos próprios
-- ---------------------------------------------------------------------
CREATE TABLE treino_exercicio (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    treino_id     INTEGER NOT NULL REFERENCES treino(id) ON DELETE CASCADE,
    exercicio_id  INTEGER NOT NULL REFERENCES exercicio(id),
    ordem         INTEGER NOT NULL CHECK (ordem >= 1),
    series        INTEGER NOT NULL CHECK (series BETWEEN 1 AND 10),
    repeticoes    TEXT    NOT NULL,              -- ex.: '12', '10-12', '30s'
    carga_kg      REAL    CHECK (carga_kg IS NULL OR carga_kg >= 0),
    descanso_seg  INTEGER NOT NULL DEFAULT 60 CHECK (descanso_seg BETWEEN 0 AND 600),
    observacao    TEXT,
    UNIQUE (treino_id, ordem)
);

-- ---------------------------------------------------------------------
-- TREINO_REALIZADO: registro de cada treino concluído pelo aluno
-- ---------------------------------------------------------------------
CREATE TABLE treino_realizado (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id       INTEGER NOT NULL REFERENCES aluno(usuario_id) ON DELETE CASCADE,
    treino_id      INTEGER NOT NULL REFERENCES treino(id) ON DELETE CASCADE,
    data           TEXT    NOT NULL,             -- 'AAAA-MM-DD'
    series_feitas  INTEGER NOT NULL CHECK (series_feitas >= 1),
    series_total   INTEGER NOT NULL CHECK (series_total >= series_feitas),
    duracao_min    INTEGER NOT NULL CHECK (duracao_min BETWEEN 1 AND 300),
    criado_em      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (aluno_id, treino_id, data)
);
CREATE INDEX idx_treino_realizado_aluno ON treino_realizado (aluno_id, data);

-- =====================================================================
-- TRIGGERS: regras de negócio garantidas também pelo banco
-- =====================================================================

-- Um aluno não pode ter duas matrículas ativas com períodos sobrepostos
CREATE TRIGGER trg_matricula_sem_sobreposicao
BEFORE INSERT ON matricula
FOR EACH ROW
WHEN NEW.status = 'ativa' AND EXISTS (
    SELECT 1 FROM matricula m
     WHERE m.aluno_id     = NEW.aluno_id
       AND m.status       = 'ativa'
       AND NEW.data_inicio <= m.data_fim
       AND NEW.data_fim    >= m.data_inicio
)
BEGIN
    SELECT RAISE(ABORT, 'O aluno já possui uma matrícula ativa nesse período.');
END;

-- Só faz check-in quem tem matrícula ativa válida naquela data
CREATE TRIGGER trg_checkin_exige_matricula
BEFORE INSERT ON checkin
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1 FROM matricula m
     WHERE m.aluno_id = NEW.aluno_id
       AND m.status   = 'ativa'
       AND NEW.data BETWEEN m.data_inicio AND m.data_fim
)
BEGIN
    SELECT RAISE(ABORT, 'Check-in recusado: o aluno não possui matrícula válida nesta data.');
END;

-- O treino concluído precisa ser um treino da ficha do próprio aluno
CREATE TRIGGER trg_treino_realizado_do_aluno
BEFORE INSERT ON treino_realizado
FOR EACH ROW
WHEN (SELECT aluno_id FROM treino WHERE id = NEW.treino_id) <> NEW.aluno_id
BEGIN
    SELECT RAISE(ABORT, 'Esse treino não pertence ao aluno.');
END;

-- =====================================================================
-- VIEWS
-- =====================================================================

-- Matrícula com nomes, situação calculada e dias restantes
CREATE VIEW vw_matriculas_situacao AS
SELECT m.*,
       u.nome      AS aluno_nome,
       u.telefone  AS aluno_telefone,
       p.nome      AS plano_nome,
       p.duracao_meses,
       CASE
         WHEN m.status = 'cancelada'           THEN 'cancelada'
         WHEN date('now', 'localtime') > m.data_fim    THEN 'vencida'
         WHEN date('now', 'localtime') < m.data_inicio THEN 'agendada'
         ELSE 'ativa'
       END AS situacao,
       CAST(julianday(m.data_fim) - julianday(date('now', 'localtime')) AS INTEGER) AS dias_restantes
  FROM matricula m
  JOIN usuario u ON u.id = m.aluno_id
  JOIN plano   p ON p.id = m.plano_id;

-- Frequência de cada aluno: total de check-ins e último check-in
CREATE VIEW vw_frequencia_alunos AS
SELECT a.usuario_id AS aluno_id,
       u.nome       AS aluno_nome,
       COUNT(c.id)  AS total_checkins,
       MAX(c.data)  AS ultimo_checkin,
       SUM(CASE WHEN c.data >= date('now', 'localtime', '-30 days') THEN 1 ELSE 0 END) AS checkins_30_dias
  FROM aluno a
  JOIN usuario u ON u.id = a.usuario_id
  LEFT JOIN checkin c ON c.aluno_id = a.usuario_id
 GROUP BY a.usuario_id, u.nome;

-- Faturamento por mês de início das matrículas (não canceladas)
CREATE VIEW vw_faturamento_mensal AS
SELECT substr(data_inicio, 1, 7) AS mes,
       COUNT(*)                  AS matriculas,
       SUM(valor_total)          AS faturamento
  FROM matricula
 WHERE status <> 'cancelada'
 GROUP BY substr(data_inicio, 1, 7);
