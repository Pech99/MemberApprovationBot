import asyncio
import logging
import json
from DB.db_manager import init_db, close_db, execute, perform
from classi.models import FormStep, JoinRequest, GroupSetup
from classi.DAO import GroupSetupDAO, JoinRequestDAO

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
        sql_select = "SELECT chat_id, steps FROM memberapprovationbot.group_setups WHERE chat_id = $1"
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


async def run_dao_tests():
    """Nuova funzione per testare l'architettura DAO e i Modelli di Dominio"""
    logging.info("=== INIZIO TEST ARCHITETTURA DAO ===")
    
    test_chat_id = 999999
    test_user_id = 123456789
    
    try:
        # 1. TEST GROUP SETUP DAO (Salvataggio Step)
        logging.info("1. Test inserimento/aggiornamento configurazione step tramite GroupSetupDAO...")
        
        # Creiamo una lista di oggetti FormStep (Modello di Dominio)
        lista_step = [
            FormStep(key="nome", type="text", question="Come ti chiami?"),
            FormStep(key="regolamento", type="button", question="Accetti il regolamento?")
        ]
        
        # Chiamiamo il metodo del DAO (ipotizzando sia un metodo statico o che accetti la lista)
        # Nota: adatta il nome del metodo a seconda di come lo hai definito in dao.py (es. save_setup, o set_steps)
        await GroupSetupDAO.save( GroupSetup(test_chat_id, lista_step))
        logging.info("✅ Configurazione Step salvata correttamente tramite DAO!")
        
        # Recuperiamo gli step appena salvati per verificare la lettura
        steps_recuperati = await GroupSetupDAO.get_by_chat_id(test_chat_id)
        logging.info(f"✅ Recupero riuscito! Step trovati: {steps_recuperati}")
        
        
        # 2. TEST JOIN REQUEST DAO (Salvataggio Richieste di Accesso)
        logging.info("2. Test inserimento richiesta di join tramite JoinRequestDAO...")
        
        # Prepariamo un dizionario fittizio con le risposte date dall'utente
        risposte_test = {
            "nome": "Mario Rossi",
            "regolamento": "Sì, accetto"
        }
        
        # Istanziamo il modello JoinRequest
        nuova_richiesta = JoinRequest(
            id = 0,
            user_id=test_user_id,
            chat_id=test_chat_id,
            username="mariorossi_tg",
            answers=risposte_test,
            status="pending"
        )
        
        # Salviamo la richiesta tramite il rispettivo DAO
        # Nota: adatta il nome del metodo (es. create_request o insert) basandoti sul tuo dao.py
        test_id = await JoinRequestDAO.create(nuova_richiesta)
        logging.info("✅ Richiesta di Join inserita correttamente tramite DAO!")
        
        # Recuperiamo le richieste pendenti di quel gruppo per verificare
        richieta = await JoinRequestDAO.get_by_id(test_id)
        logging.info(f"✅ Richiesta recuperata: {richieta}")

    except Exception as e:
        logging.error(f"❌ TEST DAO FALLITO con errore:\n{e}")
        raise e


async def main():
    logging.info("=== TEST DAO ===")
    # Inizializziamo il pool di connessioni una sola volta all'inizio (legge database.ini e setta lo schema)
    await init_db()
    
    try:
        # Eseguiamo il nuovo test incentrato sui DAO
        await run_dao_tests()
        
    finally:
        # Ci assicuriamo di chiudere il pool di connessioni alla fine di tutto
        logging.info("Chiusura del pool di connessioni in corso...")
        await close_db()
        logging.info("=== FINE TEST DAO ===")

if __name__ == "__main__":
    # Avviamo il ciclo asincrono
    asyncio.run(run_database_tests())
    asyncio.run(main())