from classi.setup import GroupSetup
from classi.settings import *
from typing import Optional
from DB import db_manager

class Chat:
    def __init__(self, id: int, type: str, name: str, setup: Optional[GroupSetup] = None, settings: Optional[Settings] = None):
        if not ChatType.isValid(type):
            raise Exception("Type invalido")
        self.id = id
        self.type = type
        self.name = name
        self.setup = setup
        self.settings = settings if settings is not None else Settings()

    def __str__(self) -> str:
        return f"{self.name} ({self.id}) - {self.type}"


class ChatType:
    Group: str = "G"
    Channel: str = "C"

    @staticmethod
    def isValid(type: str) -> bool:
        x = ["G", "C"]
        return x.count(type) > 0


class ChatDAO:
    @staticmethod
    async def get_by_id(id: int) -> Chat:
        sql = "SELECT * FROM memberapprovationbot.chat WHERE id = $1"
        res = await db_manager.execute(sql, (id,))
        
        if not res:
            return None

        row = res[0]
        return Chat(
            id = row['id'],
            type = row['tipo'],
            name = row['nome'],
            setup = GroupSetup.fromJSON(row['setup']),
            settings = Settings.fromJSON(row['settings'])
        ) 


    @staticmethod
    async def save(ch: Chat) -> bool:
        setup_json = ch.setup.toJSON()
        settings_json = ch.settings.toJSON()
        sql = """
            INSERT INTO memberapprovationbot.chat (id, tipo, nome, setup, settings) 
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) 
            DO UPDATE SET nome = EXCLUDED.nome, setup = EXCLUDED.setup, settings = EXCLUDED.settings
        """
        return await db_manager.perform(sql, (ch.id, ch.type, ch.name, setup_json, settings_json)) > 0


