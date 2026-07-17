import asyncio
import logging
import json
from db_manager import init_db, close_db, execute, perform

# Configura il logging per vedere eventuali errori o messaggi di log
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def run_database_tests():
    logging.info("=== INIZIO TEST DATABASE ===")
    
    try:
        # 1. Test Inizializzazione della Connessione
        logging.info("Tentativo di connessione al database e impostazione dello schema...")
        await init_db()
        logging.info(" Connessione riuscita e search_path impostato.")
        
        # 2. Test della funzione PERFORM (Scrittura / Inserimento dati)
        # Creiamo un setup di prova per una chat fittizia (es. chat_id: 999999)
        test_chat_id = 999999
        test_steps = json.dumps([
            {"key": "nome", "type": "text", "question": "Come ti chiami?"},
            {"key": "regolamento", "type": "button", "question": "Accetti il regolamento?"}
        ])
        
        sql_insert = """
            INSERT INTO memberapprovationbot.group_setups (chat_id, steps) 
            VALUES ($1, $2)
            ON CONFLICT (chat_id) 
            DO UPDATE SET steps = EXCLUDED.steps
        """
        
        logging.info(f"Esecuzione di perform() per inserire/aggiornare il setup di test per chat_id {test_chat_id}...")
        rows_affected = await perform(sql_insert, (test_chat_id, test_steps))
        logging.info(f" perform() eseguito con successo. Righe coinvolte/Stato: {rows_affected}")
        
        # 3. Test della funzione EXECUTE (Lettura dati)
        sql_select = "SELECT chat_id, steps FROM group_setups WHERE chat_id = $1"
        logging.info(f"Esecuzione di execute() per leggere i dati appena inseriti...")
        results = await execute(sql_select, (test_chat_id,))
        
        logging.info(f" Risultati ricevuti (Tipo: {type(results)}):")
        print(json.dumps(results, indent=4, ensure_ascii=False))
        
        # Semplice asserzione di controllo
        if results and results[0]['chat_id'] == test_chat_id:
            logging.info(" Il record estratto corrisponde a quello inserito. Mappatura dizionario OK!")
        else:
            logging.error("❌ Il record estratto non corrisponde o la lista è vuota.")
            
    except Exception as e:
        logging.error(f"❌ TEST FALLITO con errore: {e}", exc_info=True)
        
    finally:
        # 4. Test della Chiusura del Pool
        logging.info("Chiusura del pool di connessioni in corso...")
        await close_db()
        logging.info("=== FINE TEST DATABASE ===")

if __name__ == "__main__":
    # Esegue il ciclo asincrono principale
    asyncio.run(run_database_tests())