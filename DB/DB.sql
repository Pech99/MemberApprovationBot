-- CREATE DATABASE MemberApprovationBotDB;
DROP SCHEMA IF EXISTS memberapprovationbot CASCADE;
CREATE SCHEMA memberapprovationbot;
SET search_path = memberapprovationbot;


-- TABELLA utente
CREATE TABLE uten (
    id          BIGINT PRIMARY KEY,
    nome        varchar,
    cogn        varchar,
    username    varchar,
    settings    JSONB
);

-- TABELLA destinazione
CREATE TABLE chat (
    id          BIGINT PRIMARY KEY,
    tipo        char NOT NULL,
    nome        varchar,
    setup       JSONB,
    settings    JSONB,
    CHECK (upper(tipo)  IN ('G', 'C'))
);

-- Salva le richieste completate in attesa di approvazione/rifiuto da parte dell'admin
-- (P) pending, (A) approved, (R) rejected, (F) forwarded
CREATE TABLE join_requests (
    id          SERIAL PRIMARY KEY,
    uten        BIGINT NOT NULL,
    chat        BIGINT NOT NULL,
    answers     JSONB,
    status      CHAR DEFAULT 'P',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approver    BIGINT,

    CHECK (upper(status) IN ('P', 'A', 'R', 'F')),

    FOREIGN KEY (approver) REFERENCES uten(id) ON UPDATE CASCADE ON DELETE NO ACTION,
    FOREIGN KEY (uten) REFERENCES uten(id) ON UPDATE CASCADE ON DELETE NO ACTION,
    FOREIGN KEY (chat) REFERENCES chat(id) ON UPDATE CASCADE ON DELETE NO ACTION
);

CREATE TABLE message (
    join_requests   BIGINT NOT NULL,
    uten            BIGINT NOT NULL,
    message         BIGINT NOT NULL,
    PRIMARY KEY(join_requests, uten),
    FOREIGN KEY (uten)          REFERENCES uten(id)          ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (join_requests) REFERENCES join_requests(id) ON UPDATE CASCADE ON DELETE CASCADE
);

-- TABELLA ruolo
-- (C) CREATOR, (A) ADMINISTRATOR, (M) MEMBER, (R) RESTRICTED, (L) LEFT, (K) KICKED
-- ('C', 'A', 'M', 'R', 'L', 'K')
CREATE TABLE ruolo (
    uten      BIGINT,
    chat      BIGINT,
    role      char,
    PRIMARY KEY(uten, chat),
    CHECK (upper(role) IN ('C', 'A', 'M', 'E')),
    FOREIGN KEY (uten) REFERENCES uten(id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (chat) REFERENCES chat(id) ON UPDATE CASCADE ON DELETE CASCADE
);