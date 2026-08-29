"""
What this file does
--------------------
Same idea as ai_service/app/config.py: a single place that reads settings
from the environment (or a local .env file), so nothing else in this
service calls os.environ directly. Two settings matter most here:

- AI_SERVICE_URL - the address of the separate AI extraction service.
- MIDNIGHT_SERVICE_URL - the address of the separate Midnight proof
  service (see midnight_service/ at the repo root). Leave this blank
  (the default) and the backend automatically uses the offline mock in
  midnight_mock.py instead - see midnight_client.py for how that fallback
  works.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    ai_service_url: str = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
    midnight_service_url: str = os.getenv("MIDNIGHT_SERVICE_URL", "")
    host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    port: int = int(os.getenv("BACKEND_PORT", "8000"))

    # Hackathon-simple: allow any origin so the static frontend/ pages (opened
    # from a file:// URL or a plain `python -m http.server`) can call this
    # API without fighting CORS. Tighten this before this is ever public.
    cors_allow_origins: list[str] = ["*"]

    @property
    def has_midnight_service(self) -> bool:
        return bool(self.midnight_service_url)


settings = Settings()
