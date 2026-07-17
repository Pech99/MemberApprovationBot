from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class FormStep:
    key: str          # Identificativo univoco dello step (es. "nome", "eta")
    type: str         # "text", "photo", "video", etc.
    question: str     # Il testo della domanda da mostrare all'utente

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "type": self.type,
            "question": self.question
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormStep':
        return cls(
            key=data["key"],
            type=data["type"],
            question=data["question"]
        )

@dataclass
class GroupSetup:
    chat_id: int
    steps: List[FormStep] = field(default_factory=list)

@dataclass
class JoinRequest:
    id: Optional[int]
    user_id: int
    chat_id: int
    username: Optional[str]
    answers: Dict[str, Any]  # Dizionario strutturato delle risposte
    status: str = "pending"