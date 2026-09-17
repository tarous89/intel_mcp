"""Explicit pilot budgets; no model choice is silently inherited from Max v1."""
from dataclasses import dataclass
import os


def bounded(name, default, minimum, maximum):
    value = int(os.environ.get(name, default))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside the validated pilot range")
    return value


@dataclass(frozen=True)
class MaxAgentConfig:
    enabled: bool
    model: str
    trial_limit: int
    discovery_limit: int
    document_limit: int
    document_characters: int
    max_turns: int
    max_minutes: int

    @classmethod
    def from_environment(cls):
        return cls(os.getenv("MAX_AGENT_ENABLED", "false").lower() == "true",
                   os.getenv("MAX_AGENT_MODEL", "").strip(),
                   bounded("MAX_AGENT_TRIAL_LIMIT", 100, 1, 100),
                   bounded("MAX_AGENT_DISCOVERY_LIMIT", 10000, 100, 20000),
                   bounded("MAX_AGENT_DOCUMENT_LIMIT", 20, 0, 100),
                   bounded("MAX_AGENT_DOCUMENT_CHARACTERS", 2000000, 0, 10000000),
                   bounded("MAX_AGENT_MAX_TURNS", 12, 1, 30),
                   bounded("MAX_AGENT_MAX_MINUTES", 180, 1, 360))

    def validate(self, settings):
        if not self.enabled or not self.model or not settings.openai_api_key:
            raise RuntimeError("Managed Max is not configured")
        if settings.engine_source != "database":
            raise RuntimeError("Managed Max requires restricted Engine database reads")
        if not settings.engine_api_url or not settings.engine_service_token:
            raise RuntimeError("Managed Max requires Engine artifact storage")
