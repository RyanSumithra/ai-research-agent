import os
from pathlib import Path
from pydantic import Field
from .schemas import Model


class Settings(Model):
    model: str = "gpt-4.1-mini"
    openai_api_key: str = Field(default="", repr=False)
    tavily_api_key: str = Field(default="", repr=False)
    tool_timeout: float = Field(default=8, gt=0)
    llm_timeout: float = Field(default=20, gt=0)
    time_budget: float = Field(default=90, gt=0)
    max_steps: int = Field(default=8, ge=3, le=12)
    min_sources: int = Field(default=3, ge=1)
    cache_ttl: int = Field(default=3600, ge=0)
    state_dir: Path = Path(".")
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    mock: bool = False
    no_cache: bool = False
    scenario: str = "good"
    input_price: float | None = Field(default=None, ge=0)
    output_price: float | None = Field(default=None, ge=0)

    @classmethod
    def from_env(cls, **overrides):
        from dotenv import load_dotenv
        load_dotenv()
        mapping = {"OPENAI_MODEL": "model", "OPENAI_API_KEY": "openai_api_key",
                   "TAVILY_API_KEY": "tavily_api_key", "TIME_BUDGET_SECONDS": "time_budget",
                   "TOOL_TIMEOUT_SECONDS": "tool_timeout", "MAX_STEPS": "max_steps",
                   "MIN_GOOD_SOURCES": "min_sources", "CACHE_TTL_SECONDS": "cache_ttl",
                   "INPUT_USD_PER_MILLION": "input_price",
                   "OUTPUT_USD_PER_MILLION": "output_price"}
        values = {field: os.environ[key] for key, field in mapping.items() if os.getenv(key)}
        return cls(**(values | overrides))
