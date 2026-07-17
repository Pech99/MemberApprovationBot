import json
from typing import Optional, List
from .models import GroupSetup, FormStep, JoinRequest
from . import db_manager  # Importiamo l'utility scritta sopra

class GroupSetupDAO:
    @staticmethod
    async def get_by_chat_id(chat_id: int) -> Optional[GroupSetup]:
        sql = "SELECT steps FROM group_setups WHERE chat_id = $1"
        res = await db_manager.execute(sql, (chat_id,))
        
        if not res:
            return None
        
        # res è una lista di dizionari, prendiamo il primo record
        raw_steps = json.loads(res[0]['steps'])
        steps_objs = [FormStep.from_dict(s) for s in raw_steps]
        return GroupSetup(chat_id=chat_id, steps=steps_objs)

    @staticmethod
    async def save_or_update(group_setup: GroupSetup) -> None:
        steps_json = json.dumps([s.to_dict() for s in group_setup.steps])
        sql = """
            INSERT INTO group_setups (chat_id, steps) 
            VALUES ($1, $2)
            ON CONFLICT (chat_id) 
            DO UPDATE SET steps = EXCLUDED.steps
        """
        await db_manager.perform(sql, (group_setup.chat_id, steps_json))


class JoinRequestDAO:
    @staticmethod
    async def create(request: JoinRequest) -> int:
        sql = """
            INSERT INTO join_requests (user_id, chat_id, username, answers, status) 
            VALUES ($1, $2, $3, $4, $5) 
            RETURNING id
        """
        answers_json = json.dumps(request.answers)
        # perform eseguirà la query e catturerà il RETURNING id rilanciandolo
        request_id = await db_manager.perform(
            sql, (request.user_id, request.chat_id, request.username, answers_json, request.status)
        )
        request.id = request_id
        return request_id

    @staticmethod
    async def get_by_id(request_id: int) -> Optional[JoinRequest]:
        sql = "SELECT id, user_id, chat_id, username, answers, status FROM join_requests WHERE id = $1"
        res = await db_manager.execute(sql, (request_id,))
        
        if not res:
            return None
            
        row = res[0]
        return JoinRequest(
            id=row['id'],
            user_id=row['user_id'],
            chat_id=row['chat_id'],
            username=row['username'],
            answers=json.loads(row['answers']),
            status=row['status']
        )

    @staticmethod
    async def update_status(request_id: int, new_status: str) -> bool:
        sql = "UPDATE join_requests SET status = $1 WHERE id = $2 AND status = 'pending'"
        rows_affected = await db_manager.perform(sql, (new_status, request_id))
        return rows_affected > 0