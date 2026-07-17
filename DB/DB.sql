-- CREATE DATABASE MemberApprovationBotDB;
DROP SCHEMA IF EXISTS memberapprovationbot CASCADE;
CREATE SCHEMA memberapprovationbot;
SET search_path = memberapprovationbot;


-- 1. Salva la sequenza di passaggi decisa dall'admin per il suo gruppo
CREATE TABLE IF NOT EXISTS group_setups (
    chat_id BIGINT PRIMARY KEY,
    steps JSONB NOT NULL  -- Esempio: [{"type": "text", "question": "Nome?"}, {"type": "photo", "question": "Invia foto"}]
);

-- 2. Salva le richieste completate in attesa di approvazione/rifiuto da parte dell'admin
CREATE TABLE IF NOT EXISTS join_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    username TEXT,
    answers JSONB NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);