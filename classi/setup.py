from typing import List, Dict, Any, Optional
import json

class Step:
    def __init__(self, key: str, type: str, question: str, question_type: Optional[str] = "Message", media: Optional[str] = None):
        if not StepType.isValid(type) or not StepType.isValid(question_type):
            raise Exception("StepType invalido")
        if question_type != StepType.Message and media == None:
            raise Exception("media dev'essre valorizzato per Media question_type")
        if question_type == StepType.Message and media != None:
            raise Exception("Media non può essere settato per domande ti tipo Message")
        self.key = key          # es. "eta"
        self.type = type        # es. "text", "photo", "video", ""
        self.question = question # es. "Quanti anni hai?"
        self.question_type = question_type

    def __str__(self) -> str:
        return f"[{self.key}, {self.type}] --> { self.question}"

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "type": self.type, "question": self.question, "question_type": self.question_type}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Step':
        return cls(
            key=data["key"], 
            type=data["type"], 
            question=data["question"], 
            question_type=data["question_type"]
            )


class GroupSetup:
    def __init__(self, steps: List[Step]):
        self.steps = steps
        self.current = 0

    def __str__(self) -> str:
        return f"{self.steps.__str__()}"
    
    def hasNext(self) -> bool:
        return self.steps and self.current < len(self.steps)-1
    
    def getNext(self) -> Step:
        if not self.hasNext():
            raise Exception("Step has no next")
        self.current += 1
        return self.steps[self.current]

    def getCurrent(self) -> Step:
        return self.steps[self.current]

    @classmethod
    def fromJSON(cls, JSON: str):
        raw_steps = json.loads(JSON)
        return GroupSetup(steps=[Step.from_dict(s) for s in raw_steps])

    def toJSON(self) -> str:
       return json.dumps([s.to_dict() for s in self.steps])


class StepType:
    Animation: str = "Animation"
    #Audio: str = "Audio"
    #Checklist: str = "Checklist"
    #Contact: str = "Contact"
    #Dice: str = "Dice"
    Document: str = "Document"
    #Gift: str = "Gift"
    LivePhoto: str = "LivePhoto"
    Location: str = "Location"
    #MediaGroup: str = "MediaGroup"
    Message: str = "Message"
    #MessageDraft: str = "MessageDraft"
    #PaidMedia: str = "PaidMedia"
    Photo: str = "Photo"
    Poll: str = "Poll"
    #Venue: str = "Venue"
    Video: str = "Video"
    VideoNote: str = "VideoNote"
    Voice: str = "Voice"

    @staticmethod
    def isValid(type: str) -> bool:
        x = [
            "Animation", 
            "Document", 
            "LivePhoto", 
            "Location", 
            "Message", 
            "Photo", 
            "Poll", 
            "Video", 
            "VideoNote", 
            "Voice", 
            ]
        return x.count(type) > 0
        