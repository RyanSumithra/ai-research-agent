import asyncio
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import httpx
from ..schemas import Evidence, ToolInput, ToolOutput
from .base import Tool

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


class SearchHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hits, self.active, self.title = [], None, ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "result__a" in attrs.get("class", ""):
            self.active, self.title = attrs.get("href"), ""

    def handle_data(self, data):
        if self.active:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "a" and self.active:
            url = self.active
            if url.startswith("//"):
                url = "https:" + url
            url = parse_qs(urlsplit(url).query).get("uddg", [url])[0]
            self.hits.append({"url": url, "title": self.title, "text": self.title})
            self.active = None


class WebSearch(Tool):
    name, cacheable = "web_search", True

    async def execute(self, request: ToolInput) -> ToolOutput | str:
        scenario = self.settings.scenario
        if self.settings.mock:
            if scenario in {"timeout", "outage_injection"}:
                await asyncio.sleep(self.settings.tool_timeout + 1)
            if scenario == "malformed":
                return (FIXTURES / "malformed.txt").read_text(encoding="utf-8")
            if scenario == "empty" or "zxqv" in request.query.lower():
                return ToolOutput()
            from .local_kb import LocalKB
            local = await LocalKB(self.settings, self.trace, self.cache).execute(request)
            docs = [doc.model_copy(update={"origin": "mock"}) for doc in local.documents]
            if scenario in {"injection", "spam"}:
                fixture = json.loads((FIXTURES / f"{scenario}.json").read_text(encoding="utf-8"))
                if scenario == "injection":
                    fixture["text"] = "Vector database startup RAG comparison with primary research and operational tradeoffs. " * 3
                docs.insert(0, Evidence(**fixture, origin="mock"))
            return ToolOutput(documents=docs[:request.limit])
        async with httpx.AsyncClient(timeout=self.settings.tool_timeout, trust_env=False) as client:
            if self.settings.tavily_api_key:
                response = await client.post("https://api.tavily.com/search", json={
                    "api_key": self.settings.tavily_api_key, "query": request.query,
                    "max_results": request.limit, "include_raw_content": False})
                response.raise_for_status()
                hits = response.json()["results"]
                return ToolOutput(documents=[Evidence(url=h["url"], title=h["title"],
                    text=h.get("content", "")[:30000]) for h in hits])
            response = await client.get("https://html.duckduckgo.com/html/", params={"q": request.query})
            response.raise_for_status()
            parser = SearchHTML()
            parser.feed(response.text[:1_000_000])
            if not parser.hits:
                return ToolOutput(warnings=["DuckDuckGo returned no usable results; possible bot challenge"])
            return ToolOutput(documents=[Evidence(**hit) for hit in parser.hits[:request.limit]])
