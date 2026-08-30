from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    PERSON_B_SERVICE_URL: str = "http://localhost:8001"
    AI_SERVICE_URL: str = "http://localhost:8001"
    AI_SERVICE_TIMEOUT: float = 60.0
    LMM_AGENT_URL: str = "http://localhost:8001"
    LMM_AGENT_API_KEY: str = ""
    LMM_AGENT_BEARER_TOKEN: str = ""
    MIDNIGHT_SERVICE_URL: str = ""
    MIDNIGHT_SERVICE_TIMEOUT: float = 60.0
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
