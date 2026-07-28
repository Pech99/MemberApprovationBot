from typing import Dict
import json

class Settings:
    def __init__(self):
        self.settings = {}

    def set(self, key: str, val: str):
        self.settings[key] = val

    def get(self, key: str) -> str:
        return self.settings.get(key, None)

    @classmethod
    def fromJSON(cls, JSON: str):
        raw_settings = json.loads(JSON)
        if not isinstance(raw_settings, Dict):
            raise ValueError("JSON not compatible")
        S = Settings()
        S.settings = raw_settings
        return S

    def toJSON(self) -> str:
       return json.dumps(self.settings)

