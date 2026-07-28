from typing import Dict
from DB import db_manager
import json

class Role:
    def __init__(self, user_id: int, grup_id: int, role: str):
        if not RolesType.isValid(role):
            raise Exception("role invalido")
        self.user_id = user_id
        self.grup_id = grup_id
        self.role = role


class RoleDAO:
    @staticmethod
    async def get_by_group_id(id: int) -> Dict[str, Role]:
        sql = "SELECT * FROM memberapprovationbot.ruolo WHERE chat = $1"
        res = await db_manager.execute(sql, (id,))
        
        if not res:
            return None

        rl = {}
        for row in res:
            rl[row["uten"]] = Role(
                user_id = row['uten'],
                grup_id = row['chat'],
                role = row['role']
            ) 
        return rl

    @staticmethod
    async def save(rl: Role, forceUpdate = False) -> bool:
        sql = """
            INSERT INTO memberapprovationbot.ruolo (uten, chat, role) 
            VALUES ($1, $2, $3)
            ON CONFLICT (uten, chat) 
            DO UPDATE SET role = EXCLUDED.role
            WHERE role IS DISTINCT FROM EXCLUDED.role AND role = 'E';
            """
        if forceUpdate:
            sql = """
            INSERT INTO memberapprovationbot.ruolo (uten, chat, role) 
            VALUES ($1, $2, $3)
            ON CONFLICT (uten, chat) 
            DO UPDATE SET role = EXCLUDED.role
            WHERE role IS DISTINCT FROM EXCLUDED.role;
            """
        return await db_manager.perform(sql, (rl.user_id, rl.grup_id, rl.role)) > 0




class RolesType:
    Creator = "C"
    Administrator = "A"
    Member = "M"
    Left = "E"
    Kicked = "E"

    @staticmethod
    def isValid(type: str) -> bool:
        x = ["C", "A", "M", "E"]
        return x.count(type) > 0