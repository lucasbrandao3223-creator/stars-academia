-- =====================================================================
--  STARS ACADEMIA - Sistema de Gestão de Academia
--  Versão MySQL / MariaDB do mesmo modelo (para a disciplina de BD)
--  O sistema roda com SQLite (database/schema.sql). Este script é a
--  implementação equivalente para MySQL Workbench / phpMyAdmin.
-- =====================================================================

DROP DATABASE IF EXISTS stars_academia;
CREATE DATABASE stars_academia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stars_academia;

CREATE TABLE academia (
    id         INT PRIMARY KEY,
    nome       VARCHAR(100) NOT NULL,
    slogan     VARCHAR(150),
    descricao  TEXT,
    endereco   VARCHAR(150),
    cidade     VARCHAR(80),
    telefone   VARCHAR(15),
    whatsapp   VARCHAR(15),
    instagram  VARCHAR(60),
    CONSTRAINT chk_academia_unica CHECK (id = 1)
) ENGINE = InnoDB;

CREATE TABLE horario_funcionamento (
    academia_id  INT NOT NULL DEFAULT 1,
    dia_semana   TINYINT NOT NULL,          -- 0 = segunda ... 6 = domingo
    abertura     TIME NOT NULL,
    fechamento   TIME NOT NULL,
    PRIMARY KEY (academia_id, dia_semana),
    CONSTRAINT chk_dia     CHECK (dia_semana BETWEEN 0 AND 6),
    CONSTRAINT chk_horario CHECK (abertura < fechamento),
    CONSTRAINT fk_horario_academia FOREIGN KEY (academia_id) REFERENCES academia(id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Generalização: dados comuns de acesso
CREATE TABLE usuario (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    telefone    VARCHAR(15),
    senha_hash  VARCHAR(255) NOT NULL,
    tipo        ENUM('aluno', 'personal', 'admin') NOT NULL,
    criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

-- Especialização 1:1 de usuario
CREATE TABLE personal (
    usuario_id     INT PRIMARY KEY,
    cref           VARCHAR(20) NOT NULL UNIQUE,
    especialidade     VARCHAR(100),
    bio               VARCHAR(500),
    anos_experiencia  TINYINT,
    ativo             BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_anos_experiencia CHECK (anos_experiencia IS NULL OR anos_experiencia BETWEEN 0 AND 60),
    CONSTRAINT fk_personal_usuario FOREIGN KEY (usuario_id) REFERENCES usuario(id) ON DELETE CASCADE
) ENGINE = InnoDB;

-- Especialização 1:1 de usuario, com personal responsável (N:1)
CREATE TABLE aluno (
    usuario_id       INT PRIMARY KEY,
    data_nascimento  DATE,
    objetivo         VARCHAR(40),
    meta_semanal     TINYINT NOT NULL DEFAULT 3,
    personal_id      INT,
    CONSTRAINT chk_meta_semanal CHECK (meta_semanal BETWEEN 1 AND 7),
    CONSTRAINT fk_aluno_usuario  FOREIGN KEY (usuario_id)  REFERENCES usuario(id) ON DELETE CASCADE,
    CONSTRAINT fk_aluno_personal FOREIGN KEY (personal_id) REFERENCES personal(usuario_id) ON DELETE SET NULL
) ENGINE = InnoDB;

CREATE TABLE plano (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    nome           VARCHAR(60) NOT NULL UNIQUE,
    descricao      VARCHAR(255),
    duracao_meses  INT NOT NULL,
    preco_mensal   DECIMAL(8, 2) NOT NULL,
    ativo          BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_duracao CHECK (duracao_meses BETWEEN 1 AND 24),
    CONSTRAINT chk_preco   CHECK (preco_mensal > 0)
) ENGINE = InnoDB;

CREATE TABLE matricula (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id         INT NOT NULL,
    plano_id         INT NOT NULL,
    data_inicio      DATE NOT NULL,
    data_fim         DATE NOT NULL,
    valor_total      DECIMAL(9, 2) NOT NULL,
    forma_pagamento  ENUM('pix', 'cartao', 'dinheiro') NOT NULL,
    status           ENUM('ativa', 'cancelada') NOT NULL DEFAULT 'ativa',
    criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_periodo CHECK (data_inicio <= data_fim),
    CONSTRAINT chk_valor   CHECK (valor_total >= 0),
    CONSTRAINT fk_matricula_aluno FOREIGN KEY (aluno_id) REFERENCES aluno(usuario_id),
    CONSTRAINT fk_matricula_plano FOREIGN KEY (plano_id) REFERENCES plano(id),
    INDEX idx_matricula_aluno (aluno_id, data_fim)
) ENGINE = InnoDB;

CREATE TABLE checkin (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id  INT NOT NULL,
    data      DATE NOT NULL,
    hora      TIME NOT NULL,
    CONSTRAINT uq_checkin_dia UNIQUE (aluno_id, data),
    CONSTRAINT fk_checkin_aluno FOREIGN KEY (aluno_id) REFERENCES aluno(usuario_id) ON DELETE CASCADE,
    INDEX idx_checkin_data (data)
) ENGINE = InnoDB;

CREATE TABLE grupo_muscular (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    nome  VARCHAR(40) NOT NULL UNIQUE
) ENGINE = InnoDB;

CREATE TABLE exercicio (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    nome               VARCHAR(80) NOT NULL UNIQUE,
    grupo_muscular_id  INT NOT NULL,
    equipamento        VARCHAR(60),
    instrucoes         VARCHAR(300),
    CONSTRAINT fk_exercicio_grupo FOREIGN KEY (grupo_muscular_id) REFERENCES grupo_muscular(id)
) ENGINE = InnoDB;

CREATE TABLE treino (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id       INT NOT NULL,
    personal_id    INT NOT NULL,
    nome           VARCHAR(80) NOT NULL,
    observacoes    VARCHAR(300),
    ativo          BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_treino_aluno    FOREIGN KEY (aluno_id)    REFERENCES aluno(usuario_id) ON DELETE CASCADE,
    CONSTRAINT fk_treino_personal FOREIGN KEY (personal_id) REFERENCES personal(usuario_id),
    INDEX idx_treino_aluno (aluno_id)
) ENGINE = InnoDB;

-- N:N entre treino e exercicio, com atributos próprios
CREATE TABLE treino_exercicio (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    treino_id     INT NOT NULL,
    exercicio_id  INT NOT NULL,
    ordem         INT NOT NULL,
    series        TINYINT NOT NULL,
    repeticoes    VARCHAR(20) NOT NULL,
    carga_kg      DECIMAL(5, 1),
    descanso_seg  SMALLINT NOT NULL DEFAULT 60,
    observacao    VARCHAR(120),
    CONSTRAINT uq_treino_ordem UNIQUE (treino_id, ordem),
    CONSTRAINT chk_ordem    CHECK (ordem >= 1),
    CONSTRAINT chk_series   CHECK (series BETWEEN 1 AND 10),
    CONSTRAINT chk_carga    CHECK (carga_kg IS NULL OR carga_kg >= 0),
    CONSTRAINT chk_descanso CHECK (descanso_seg BETWEEN 0 AND 600),
    CONSTRAINT fk_te_treino    FOREIGN KEY (treino_id)    REFERENCES treino(id) ON DELETE CASCADE,
    CONSTRAINT fk_te_exercicio FOREIGN KEY (exercicio_id) REFERENCES exercicio(id)
) ENGINE = InnoDB;

-- Registro de cada treino concluído pelo aluno
CREATE TABLE treino_realizado (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id       INT NOT NULL,
    treino_id      INT NOT NULL,
    data           DATE NOT NULL,
    series_feitas  SMALLINT NOT NULL,
    series_total   SMALLINT NOT NULL,
    duracao_min    SMALLINT NOT NULL,
    criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_treino_realizado_dia UNIQUE (aluno_id, treino_id, data),
    CONSTRAINT chk_series_feitas CHECK (series_feitas >= 1),
    CONSTRAINT chk_series_total  CHECK (series_total >= series_feitas),
    CONSTRAINT chk_duracao_treino CHECK (duracao_min BETWEEN 1 AND 300),
    CONSTRAINT fk_tr_aluno  FOREIGN KEY (aluno_id)  REFERENCES aluno(usuario_id) ON DELETE CASCADE,
    CONSTRAINT fk_tr_treino FOREIGN KEY (treino_id) REFERENCES treino(id) ON DELETE CASCADE,
    INDEX idx_treino_realizado_aluno (aluno_id, data)
) ENGINE = InnoDB;

-- =====================================================================
-- TRIGGERS
-- =====================================================================
DELIMITER $$

CREATE TRIGGER trg_matricula_sem_sobreposicao
BEFORE INSERT ON matricula
FOR EACH ROW
BEGIN
    IF NEW.status = 'ativa' AND EXISTS (
        SELECT 1 FROM matricula m
         WHERE m.aluno_id = NEW.aluno_id AND m.status = 'ativa'
           AND NEW.data_inicio <= m.data_fim AND NEW.data_fim >= m.data_inicio
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'O aluno já possui uma matrícula ativa nesse período.';
    END IF;
END$$

CREATE TRIGGER trg_checkin_exige_matricula
BEFORE INSERT ON checkin
FOR EACH ROW
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM matricula m
         WHERE m.aluno_id = NEW.aluno_id AND m.status = 'ativa'
           AND NEW.data BETWEEN m.data_inicio AND m.data_fim
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Check-in recusado: o aluno não possui matrícula válida nesta data.';
    END IF;
END$$

CREATE TRIGGER trg_treino_realizado_do_aluno
BEFORE INSERT ON treino_realizado
FOR EACH ROW
BEGIN
    IF (SELECT aluno_id FROM treino WHERE id = NEW.treino_id) <> NEW.aluno_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Esse treino não pertence ao aluno.';
    END IF;
END$$

DELIMITER ;

-- =====================================================================
-- VIEWS
-- =====================================================================
CREATE VIEW vw_matriculas_situacao AS
SELECT m.*, u.nome AS aluno_nome, u.telefone AS aluno_telefone, p.nome AS plano_nome, p.duracao_meses,
       CASE
         WHEN m.status = 'cancelada'     THEN 'cancelada'
         WHEN CURDATE() > m.data_fim     THEN 'vencida'
         WHEN CURDATE() < m.data_inicio  THEN 'agendada'
         ELSE 'ativa'
       END AS situacao,
       DATEDIFF(m.data_fim, CURDATE()) AS dias_restantes
  FROM matricula m
  JOIN usuario u ON u.id = m.aluno_id
  JOIN plano   p ON p.id = m.plano_id;

CREATE VIEW vw_frequencia_alunos AS
SELECT a.usuario_id AS aluno_id, u.nome AS aluno_nome,
       COUNT(c.id) AS total_checkins, MAX(c.data) AS ultimo_checkin,
       SUM(CASE WHEN c.data >= CURDATE() - INTERVAL 30 DAY THEN 1 ELSE 0 END) AS checkins_30_dias
  FROM aluno a
  JOIN usuario u ON u.id = a.usuario_id
  LEFT JOIN checkin c ON c.aluno_id = a.usuario_id
 GROUP BY a.usuario_id, u.nome;

CREATE VIEW vw_faturamento_mensal AS
SELECT DATE_FORMAT(data_inicio, '%Y-%m') AS mes, COUNT(*) AS matriculas, SUM(valor_total) AS faturamento
  FROM matricula
 WHERE status <> 'cancelada'
 GROUP BY DATE_FORMAT(data_inicio, '%Y-%m');

-- =====================================================================
-- DADOS INICIAIS (o restante é gerado pelo sistema)
-- =====================================================================
INSERT INTO academia VALUES (1, 'STARS Academia', 'Treine como uma estrela.',
    'Musculação, aeróbico e acompanhamento de personal trainer.', 'Av. das Estrelas, 500 - Centro',
    'São Paulo - SP', '1132450500', '11987650500', '@starsacademia');

INSERT INTO horario_funcionamento (academia_id, dia_semana, abertura, fechamento) VALUES
    (1, 0, '06:00', '23:00'), (1, 1, '06:00', '23:00'), (1, 2, '06:00', '23:00'), (1, 3, '06:00', '23:00'),
    (1, 4, '06:00', '23:00'), (1, 5, '08:00', '18:00'), (1, 6, '08:00', '12:00');

INSERT INTO plano (nome, duracao_meses, preco_mensal, descricao) VALUES
    ('Mensal', 1, 119.90, 'Sem fidelidade.'),
    ('Trimestral', 3, 104.90, '3 meses com desconto.'),
    ('Semestral', 6, 94.90, '6 meses.'),
    ('Anual', 12, 84.90, 'O melhor preço.');

INSERT INTO grupo_muscular (nome) VALUES
    ('Peito'), ('Costas'), ('Ombros'), ('Bíceps'), ('Tríceps'), ('Pernas'), ('Glúteos'), ('Abdômen'), ('Cardio');

-- =====================================================================
-- CONSULTAS DE EXEMPLO (usadas no painel)
-- =====================================================================

-- 1) Alunos com plano vencendo nos próximos 7 dias
-- SELECT aluno_nome, aluno_telefone, plano_nome, data_fim, dias_restantes
--   FROM vw_matriculas_situacao
--  WHERE situacao = 'ativa' AND dias_restantes BETWEEN 0 AND 7
--  ORDER BY data_fim;

-- 2) Horários de pico (check-ins por hora nos últimos 30 dias)
-- SELECT HOUR(hora) AS hora, COUNT(*) AS total
--   FROM checkin WHERE data >= CURDATE() - INTERVAL 30 DAY
--  GROUP BY HOUR(hora) ORDER BY hora;

-- 3) Ficha completa de um treino
-- SELECT te.ordem, e.nome, g.nome AS grupo, te.series, te.repeticoes, te.carga_kg, te.descanso_seg
--   FROM treino_exercicio te
--   JOIN exercicio e      ON e.id = te.exercicio_id
--   JOIN grupo_muscular g ON g.id = e.grupo_muscular_id
--  WHERE te.treino_id = 1 ORDER BY te.ordem;

-- 4) Alunos ativos de cada personal
-- SELECT pu.nome AS personal, COUNT(a.usuario_id) AS alunos
--   FROM personal p JOIN usuario pu ON pu.id = p.usuario_id
--   LEFT JOIN aluno a ON a.personal_id = p.usuario_id
--  GROUP BY p.usuario_id, pu.nome;
