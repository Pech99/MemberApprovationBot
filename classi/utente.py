from typing import Optional
from DB import db_manager
import json

from classi.settings import *
from classi.setup import *

class Utente:
    def __init__(self, id: int, name: str, surname: Optional[str] = None, username: Optional[str] = None, settings: Optional[Settings] = None):
        self.id = id
        self.name = name
        self.surname = surname
        self.username = username
        self.settings = settings if settings is not None else Settings()

    def __str__(self) -> str:
        return f"{self.name} ({self.id}) - {self.username}"


class UtenteDAO:
    @staticmethod
    async def get_by_id(id: int) -> Utente:
        sql = "SELECT * FROM memberapprovationbot.uten WHERE id = $1"
        res = await db_manager.execute(sql, (id,))
        
        if not res:
            return None

        row = res[0]
        return Utente(
            id = row['id'],
            name = row['nome'],
            surname = row['cogn'],
            username = row['username'],
            settings = Settings.fromJSON(row['settings'])
        ) 


    @staticmethod
    async def save(usr: Utente) -> bool:
        settings_json = usr.settings.toJSON()
        sql = """
            INSERT INTO memberapprovationbot.uten (id, nome, cogn, username, settings) 
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) 
            DO UPDATE SET nome = EXCLUDED.nome, cogn = EXCLUDED.cogn, username = EXCLUDED.username, settings = EXCLUDED.settings
            """
        return await db_manager.perform(sql, (usr.id, usr.name, usr.surname, usr.username, settings_json)) > 0


