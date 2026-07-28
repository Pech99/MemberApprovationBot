from typing import Dict, Any, Optional
from typing import Optional
from DB import db_manager
import json

class JoinRequestStatus:
    Pending: str = 'P'
    Approved: str = 'A'
    Rejected: str = 'R'
    Forwarded: str = "F"

    @staticmethod
    def isValid(type: str) -> bool:
        x = ["P", "A", "R", "F"]
        return x.count(type) > 0

class JoinRequest:
    def __init__(self, user_id: int, chat_id: int, id: Optional[int] = -1, answers: Optional[Dict[str, Any]] = None, status: Optional[str] = JoinRequestStatus.Pending, approver: Optional[int] = None):
        if not JoinRequestStatus.isValid(status):
            raise Exception("StepType invalido")
        self.id = id
        self.user_id = user_id
        self.chat_id = chat_id
        self.answers = answers if answers is not None else {}
        self.status = status
        self.approver = approver

    def __str__(self) -> str:
        return f"{self.user_id} --> {self.chat_id}: {self.status}"



class JoinRequestDAO:
    @staticmethod
    async def create(request: JoinRequest) -> int:
        sql = """
            INSERT INTO memberapprovationbot.join_requests (uten, chat, answers, status) 
            VALUES ($1, $2, $3, $4) 
            RETURNING id
        """
        answers_json = json.dumps(request.answers)
        request_id = await db_manager.perform(
            sql, (request.user_id, request.chat_id, answers_json, request.status)
        )
        request.id = request_id
        return request_id

    @staticmethod
    async def get_by_id(request_id: int) -> JoinRequest:
        sql = "SELECT * FROM memberapprovationbot.join_requests WHERE id = $1"
        res = await db_manager.execute(sql, (request_id,))
        
        if not res:
            return None
            
        row = res[0]
        return JoinRequest(
            id=row['id'],
            user_id=row['uten'],
            chat_id=row['chat'],
            answers=json.loads(row['answers']),
            status=row['status'],
            approver = row['approver']
        )

    @staticmethod
    async def get_by_chat_ids(chat_id: int, user_id: int) -> JoinRequest:
        sql = "SELECT * FROM memberapprovationbot.join_requests WHERE chat = $1 AND uten = $2"
        res = await db_manager.execute(sql, (chat_id, user_id))
        if not res:
            return None
            
        row = res[0]
        return JoinRequest(
            id=row['id'],
            user_id=row['uten'],
            chat_id=row['chat'],
            answers=json.loads(row['answers']),
            status=row['status'],
            approver = row['approver']
        )

    @staticmethod
    async def update_approver(request_id: int, approver: int) -> bool:
        sql = "UPDATE memberapprovationbot.join_requests SET approver = $1 WHERE id = $2"
        rows_affected = await db_manager.perform(sql, (approver, request_id))
        return rows_affected > 0

    @staticmethod
    async def update_answers(request_id: int, answers: str) -> bool:
        sql = "UPDATE memberapprovationbot.join_requests SET answers = $1 WHERE id = $2"
        rows_affected = await db_manager.perform(sql, (answers, request_id))
        return rows_affected > 0


    @staticmethod
    async def update_status(request_id: int, new_status: str) -> bool:
        sql = "UPDATE memberapprovationbot.join_requests SET status = $1 WHERE id = $2 AND status = 'P'"
        rows_affected = await db_manager.perform(sql, (new_status, request_id))
        return rows_affected > 0