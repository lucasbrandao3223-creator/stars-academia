-- STARS Academia - Modelo Fisico
-- Projeto Integrado DWS + POO + BD

CREATE DATABASE IF NOT EXISTS stars_academia;
USE stars_academia;

CREATE TABLE Aluno (
    id_aluno INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    telefone VARCHAR(15),
    data_nasc DATE
);

CREATE TABLE Personal (
    id_personal INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cref VARCHAR(20) NOT NULL UNIQUE,
    especialidade VARCHAR(50)
);

CREATE TABLE Plano (
    id_plano INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL,
    duracao INT NOT NULL,
    preco DECIMAL(8,2) NOT NULL,
    CHECK (duracao > 0),
    CHECK (preco > 0)
);

CREATE TABLE Matricula (
    id_matricula INT AUTO_INCREMENT PRIMARY KEY,
    id_aluno INT NOT NULL,
    id_plano INT NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ativa',
    CHECK (data_fim >= data_inicio),
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_plano) REFERENCES Plano(id_plano)
);

CREATE TABLE Checkin (
    id_checkin INT AUTO_INCREMENT PRIMARY KEY,
    id_aluno INT NOT NULL,
    data DATE NOT NULL,
    hora TIME NOT NULL,
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno)
);

CREATE TABLE Treino (
    id_treino INT AUTO_INCREMENT PRIMARY KEY,
    id_aluno INT NOT NULL,
    id_personal INT NOT NULL,
    nome_treino VARCHAR(50) NOT NULL,
    observacao VARCHAR(200),
    FOREIGN KEY (id_aluno) REFERENCES Aluno(id_aluno),
    FOREIGN KEY (id_personal) REFERENCES Personal(id_personal)
);

CREATE TABLE Exercicio (
    id_exercicio INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL,
    grupo_muscular VARCHAR(30)
);

-- tabela do relacionamento N:N "contem" (Treino x Exercicio)
CREATE TABLE contem (
    id_treino INT NOT NULL,
    id_exercicio INT NOT NULL,
    series INT NOT NULL,
    repeticoes INT NOT NULL,
    carga DECIMAL(5,1),
    CHECK (series > 0),
    CHECK (repeticoes > 0),
    PRIMARY KEY (id_treino, id_exercicio),
    FOREIGN KEY (id_treino) REFERENCES Treino(id_treino),
    FOREIGN KEY (id_exercicio) REFERENCES Exercicio(id_exercicio)
);
