import json
from typing import List, Dict, Any, Optional

class FormStep:
    def __init__(self, key: str, type: str, question: str):
        self.key = key          # es. "eta"
        self.type = type        # es. "text", "photo", "video"
        self.question = question # es. "Quanti anni hai?"

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "type": self.type, "question": self.question}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormStep':
        return cls(key=data["key"], type=data["type"], question=data["question"])


class GroupSetup:
    def __init__(self, chat_id: int, steps: List[FormStep]):
        self.chat_id = chat_id
        self.steps = steps


class JoinRequest:
    def __init__(self, id: Optional[int], user_id: int, chat_id: int, username: Optional[str], answers: Dict[str, Any], status: str = "pending"):
        self.id = id
        self.user_id = user_id
        self.chat_id = chat_id
        self.username = username
        self.answers = answers  # Dizionario con le risposte dell'utente
        self.status = status