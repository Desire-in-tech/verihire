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
    # Anthropic API key. Get one at https://console.anthropic.com/
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")

    # Which Claude model to call. Set this to whatever current model name
    # your Anthropic console shows you (model IDs change over time, so we
    # deliberately don't hardcode one here) - anthropic docs also list them at
    # https://docs.claude.com/en/docs/about-claude/models
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

    # Host/port this service listens on.
    host: str = os.getenv("AI_SERVICE_HOST", "0.0.0.0")
    port: int = int(os.getenv("AI_SERVICE_PORT", "8001"))

    @property
    def has_ai(self) -> bool:
        """True if a real Anthropic call can be made; False => offline fallback mode."""
        return bool(self.anthropic_api_key)


settings = Settings()
