import asyncio
import json
from pathlib import Path
import httpx
import pytest
from research_agent.cache import Cache
from research_agent.schemas import ToolInput, ToolOutput
from research_agent.tools.base import Tool
from research_agent.tools.fetch_page import FetchPage
from research_agent.tools.web_search import WebSearch


class Broken(Tool):
    name = "broken"
    calls = 0

    async def execute(self, request):
        self.calls += 1
        return '{"documents":"wrong"}'


def test_malformed_schema_retried_once(settings, context):
    tool = Broken(settings, *context)
    result = asyncio.run(tool.run(ToolInput(query="research")))
    assert tool.calls == 2
    assert result.warnings and not result.documents


def test_repair_can_recover(settings, context):
    class Repair(Broken):
        async def execute(self, request):
            self.calls += 1
            return {"documents": "bad"} if self.calls == 1 else ToolOutput()
    tool = Repair(settings, *context)
    result = asyncio.run(tool.run(ToolInput(query="research")))
    assert tool.calls == 2 and not result.warnings


def test_timeout_returns_warning(settings, context):
    settings.scenario = "timeout"
    result = asyncio.run(WebSearch(settings, *context).run(ToolInput(query="vector database")))
    assert not result.documents and result.warnings
    events = [json.loads(line) for line in context[0].path.read_text().splitlines()]
    assert len([e for e in events if e["name"] == "tool_error"]) == 2


def test_cache_ttl_and_corruption(tmp_path):
    cache = Cache(tmp_path, ttl=3600)
    from research_agent.schemas import Evidence
    output = ToolOutput(documents=[Evidence(url="https://example.com", title="Example", text="text")])
    cache.put("key", output)
    assert cache.get("key") == output
    cache.path("key").write_text("broken")
    assert cache.get("key") is None
    cache.put("key", output)
    row = json.loads(cache.path("key").read_text())
    row["created"] = 0
    cache.path("key").write_text(json.dumps(row))
    assert cache.get("key") is None


def test_mock_live_cache_isolation(settings, context):
    settings.no_cache = False
    cache = Cache(settings.state_dir, 3600)
    tool = WebSearch(settings, context[0], cache)
    output = asyncio.run(tool.run(ToolInput(query="vector database RAG")))
    assert output.documents
    assert all(doc.origin == "mock" for doc in output.documents)
    settings.scenario = "empty"
    result = asyncio.run(WebSearch(settings, context[0], cache).run(ToolInput(query="vector database RAG")))
    assert not result.documents


def test_page_fixture_is_quarantinable(settings, context):
    from research_agent.safety import suspicious
    result = asyncio.run(FetchPage(settings, *context).run(ToolInput(
        query="vector database", url="https://fixture.example/malicious")))
    assert suspicious(result.documents[0].text)


def test_fetch_pins_ip_and_blocks_redirect_to_private(settings, context, monkeypatch):
    import research_agent.tools.fetch_page as module
    settings.mock = False
    seen = []
    async def resolve(url):
        if "127.0.0.1" in url:
            raise ValueError("private redirect")
        return "example.com", "93.184.216.34", 443
    def handle(request):
        seen.append(request)
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})
    original_client = httpx.AsyncClient
    monkeypatch.setattr(module, "resolve_public", resolve)
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: original_client(
        transport=httpx.MockTransport(handle), **kw))
    result = asyncio.run(FetchPage(settings, *context).run(ToolInput(query="test", url="https://example.com")))
    assert result.warnings and not result.documents
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "example.com"
    assert seen[0].extensions["sni_hostname"] == "example.com"


@pytest.mark.parametrize("kind,body", [("application/pdf", b"pdf"), ("text/plain", b"x"*500001)])
def test_fetch_rejects_nontext_and_oversize(settings, context, monkeypatch, kind, body):
    import research_agent.tools.fetch_page as module
    settings.mock = False
    async def resolve(url):
        return "example.com", "93.184.216.34", 443
    original_client = httpx.AsyncClient
    monkeypatch.setattr(module, "resolve_public", resolve)
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: original_client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200,
            headers={"content-type": kind}, content=body)), **kw))
    result = asyncio.run(FetchPage(settings, *context).run(ToolInput(query="test", url="https://example.com")))
    assert not result.documents and result.warnings
