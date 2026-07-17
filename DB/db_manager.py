import asyncio
from configparser import ConfigParser
from typing import Optional, List, Dict, Any
import asyncpg

def load_config(filename='database.ini', section='postgresql') -> dict:
    parser = ConfigParser()
    parser.read(filename)
    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            # asyncpg vuole 'database' invece di 'dbname' se usi parametri scompattati,
            # oppure passiamo direttamente la DSN string, ma per compatibilità mappiamo:
            key = 'database' if param[0] == 'dbname' else param[0]
            config[key] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {filename} file')
    return config

# Pool di connessione globale gestito asincronamente
_pool: Optional[asyncpg.Pool] = None

async def init_db():
    """Inizializza il pool globale all'avvio del bot"""
    global _pool
    config = load_config()
    _pool = await asyncpg.create_pool(**config)
    
    # Imposta lo schema (search_path) all'avvio
    #async with _pool.acquire() as conn:
    #    await conn.execute("SET search_path TO memberapprovationbot")
    print('Connected to the PostgreSQL server and schema set.')

async def close_db():
    """Chiude il pool alla chiusura del bot"""
    if _pool:
        await _pool.close()

async def execute(sql: str, args: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """Esegue una query di selezione e restituisce una lista di dizionari"""
    if not _pool:
        raise Exception("Database pool non inizializzato. Chiama init_db() all'avvio.")
    try:
        async with _pool.acquire() as conn:
            # asyncpg usa $1, $2, $3 al posto di %s o ?.
            if args:
                rows = await conn.fetch(sql, *args)
            else:
                rows = await conn.fetch(sql)
            
            # Convertiamo i Record di asyncpg in normali dict Python
            return [dict(row) for row in rows]
    except Exception as error:
        raise Exception(f"execute: errore sulla query {sql} args={args}\n{error}")

async def perform(sql: str, args: Optional[tuple] = None) -> int:
    """Esegue comandi di INSERT, UPDATE, DELETE e restituisce il numero di righe modificate o l'ID se presente"""
    if not _pool:
        raise Exception("Database pool non inizializzato.")
    try:
        async with _pool.acquire() as conn:
            if args:
                # Se la query contiene RETURNING, usiamo fetchval per prendere l'ID inserito
                if "RETURNING" in sql.upper():
                    res = await conn.fetchval(sql, *args)
                    return res if res is not None else 1
                status = await conn.execute(sql, *args)
            else:
                if "RETURNING" in sql.upper():
                    res = await conn.fetchval(sql)
                    return res if res is not None else 1
                status = await conn.execute(sql)
            
            # Il metodo execute restituisce una stringa di stato (es: "UPDATE 5")
            # Estraiamo il numero finale di righe coinvolte
            try:
                parts = status.split()
                return int(parts[-1]) if parts else -1
            except ValueError:
                return 1
    except Exception as error:
        raise Exception(f"perform: errore sulla query {sql} args={args}\n{error}")