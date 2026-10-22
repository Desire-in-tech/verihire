"""
What this file does
--------------------
Reads configuration from environment variables (or a local `.env` file) so
that secrets like the Anthropic API key never get hardcoded into the source
code. Every other module in this service imports `settings` from here
instead of calling `os.environ` directly, so there is exactly one place
that knows about env vars.

If `ANTHROPIC_API_KEY` is not set, `settings.has_ai` is False and
`extraction.py` automatically falls back to a offline keyword-based
extractor, so the service (and the demo) still works without an API key.
"""

import os
from dotenv import load_dotenv

# Loads variables from a ".env" file in this directory into the process
# environment, if that file exists. Safe to call even if it doesn't.
load_dotenv()


class Settings:
    # Values are read on each access so a process can be configured without
    # baking secrets into the module, and so tests see the current environment.

    @property
    def anthropic_api_key(self) -> str | None:
        return os.getenv("ANTHROPIC_API_KEY") or None

    @property
    def anthropic_model(self) -> str:
        # Model IDs change. Override ANTHROPIC_MODEL with the current console name.
        return os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

    @property
    def host(self) -> str:
        return os.getenv("AI_SERVICE_HOST", "0.0.0.0")

    @property
    def port(self) -> int:
        return int(os.getenv("AI_SERVICE_PORT", "8001"))

    @property
    def service_token(self) -> str:
        return os.getenv("AI_SERVICE_TOKEN", "").strip()

    @property
    def auth_configured(self) -> bool:
        return bool(self.service_token)

    @property
    def has_ai(self) -> bool:
        """True if a real Anthropic call can be made; False => offline fallback mode."""
        return bool(self.anthropic_api_key)


settings = Settings()
