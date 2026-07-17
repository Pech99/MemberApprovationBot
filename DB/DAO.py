import json
import asyncpg
from typing import Optional, List
from .models import GroupSetup, FormStep, JoinRequest  # Adatta gli import al tuo progetto

class GroupSetupDAO:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_by_chat_id(self, chat_id: int) -> Optional[GroupSetup]:
        """Recupera la configurazione degli step per un determinato gruppo"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT steps FROM group_setups WHERE chat_id = $1", 
                chat_id
            )
            if not row:
                return None
                
            raw_steps = json.loads(row['steps'])
            steps_objs = [FormStep.from_dict(s) for s in raw_steps]
            return GroupSetup(chat_id=chat_id, steps=steps_objs)

    async def save_or_update(self, group_setup: GroupSetup) -> None:
        """Salva o aggiorna il setup di un gruppo"""
        steps_json = json.dumps([s.to_dict() for s in group_setup.steps])
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO group_setups (chat_id, steps) 
                VALUES ($1, $2)
                ON CONFLICT (chat_id) 
                DO UPDATE SET steps = EXCLUDED.steps
                """,
                group_setup.chat_id, steps_json
            )


class JoinRequestDAO:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, request: JoinRequest) -> int:
        """Salva una nuova richiesta di join e restituisce l'ID generato"""
        async with self.pool.acquire() as conn:
            request_id = await conn.fetchval(
                """
                INSERT INTO join_requests (user_id, chat_id, username, answers, status) 
                VALUES ($1, $2, $3, $4, $5) 
                RETURNING id
                """,
                request.user_id, 
                request.chat_id, 
                request.username, 
                json.dumps(request.answers), 
                request.status
            )
            request.id = request_id
            return request_id

    async def get_by_id(self, request_id: int) -> Optional[JoinRequest]:
        """Recupera una singola richiesta tramite ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id, chat_id, username, answers, status FROM join_requests WHERE id = $1",
                request_id
            )
            if not row:
                return None
                
            return JoinRequest(
                id=row['id'],
                user_id=row['user_id'],
                chat_id=row['chat_id'],
                username=row['username'],
                answers=json.loads(row['answers']),
                status=row['status']
            )

    async def update_status(self, request_id: int, new_status: str) -> bool:
        """Aggiorna lo stato della richiesta (es. 'approved', 'rejected')"""
        async with self.pool.acquire() as conn:
            status = await conn.execute(
                "UPDATE join_requests SET status = $1 WHERE id = $2 AND status = 'pending'",
                new_status, request_id
            )
            # Ritorna True se ha effettivamente aggiornato una riga, False altrimenti
            return status == "UPDATE 1"