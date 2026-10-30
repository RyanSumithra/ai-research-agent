import pytest
from research_agent.cache import Cache
from research_agent.config import Settings
from research_agent.tracing import Trace


@pytest.fixture
def settings(tmp_path):
    return Settings(mock=True, state_dir=tmp_path, tool_timeout=0.02, no_cache=True)


@pytest.fixture
def context(settings):
    trace = Trace(settings.state_dir)
    return trace, Cache(settings.state_dir, settings.cache_ttl, False)
