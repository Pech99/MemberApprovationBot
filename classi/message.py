from typing import Dict
from DB import db_manager
import json

class Message:
    def __init__(self, user_id: int, join_requests_id: int, message: int):
        self.user_id = user_id
        self.join_requests_id = join_requests_id
        self.message = message


class MessageDAO:
    @staticmethod
    async def get_by_join_requests_id(id: int) -> Dict[str, Message]:
        sql = "SELECT * FROM memberapprovationbot.message WHERE join_requests = $1"
        res = await db_manager.execute(sql, (id,))
        
        if not res:
            return None

        mg = {}
        for row in res:
            mg[row["uten"]] = Message(
                user_id = row['uten'],
                join_requests_id = row['join_requests'],
                message = row['message']
            ) 
        return mg

    @staticmethod
    async def save(mg: Message) -> bool:
        sql = """
            INSERT INTO memberapprovationbot.message (join_requests, uten, message) 
            VALUES ($1, $2, $3)
            ON CONFLICT (join_requests, uten) 
            DO UPDATE SET message = EXCLUDED.message
            WHERE message IS DISTINCT FROM EXCLUDED.message
            """
        return await db_manager.perform(sql, (mg.join_requests_id, mg.user_id, mg.message)) > 0
