from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    AI_SERVICE_URL: str = "http://localhost:8001"
    # Leave blank to use the offline mock proof (midnight_mock.py). Set it
    # once midnight_service/ is actually running to switch on real proofs.
    MIDNIGHT_SERVICE_URL: str = ""

    class Config:
        env_file = ".env"

    @property
    def has_midnight_service(self) -> bool:
        return bool(self.MIDNIGHT_SERVICE_URL)

@lru_cache()
def get_settings():
    return Settings()
