import json
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import httpx
from ..safety import resolve_public
from ..schemas import Evidence, ToolInput, ToolOutput
from .base import Tool
from .web_search import FIXTURES


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts, self.title_parts = [], []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer", "noscript"}:
            self.skip += 1
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "noscript"}:
            self.skip = max(0, self.skip - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data.strip())
        if self.in_title:
            self.title_parts.append(data.strip())


class FetchPage(Tool):
    name, cacheable = "fetch_page", True

    async def execute(self, request: ToolInput) -> ToolOutput:
        if not request.url:
            raise ValueError("fetch_page requires a URL")
        if self.settings.mock:
            for path in self.settings.data_dir.glob("*.json"):
                doc = json.loads(path.read_text(encoding="utf-8"))
                if doc["url"] == request.url:
                    return ToolOutput(documents=[Evidence(**doc, origin="mock")])
            for fixture in ("injection", "spam"):
                doc = json.loads((FIXTURES / f"{fixture}.json").read_text(encoding="utf-8"))
                if doc["url"] == request.url:
                    return ToolOutput(documents=[Evidence(**doc, origin="mock")])
            return ToolOutput(warnings=["URL absent from offline fixtures"])
        url = request.url
        # Pin the transport URL to the checked IP. Host and TLS SNI retain the hostname.
        async with httpx.AsyncClient(timeout=self.settings.tool_timeout, trust_env=False,
                                     follow_redirects=False,
                                     limits=httpx.Limits(max_keepalive_connections=0)) as client:
            for _ in range(4):
                host, ip, port = await resolve_public(url)
                target = httpx.URL(url).copy_with(host=ip)
                host_header = f"[{host}]" if ":" in host else host
                default_port = 443 if urlsplit(url).scheme == "https" else 80
                if port != default_port:
                    host_header += f":{port}"
                async with client.stream("GET", target, headers={"Host": host_header,
                        "User-Agent": "ResearchAgent/0.1"},
                        extensions={"sni_hostname": host}) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers["location"])
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(kind in content_type for kind in ("text/html", "text/plain")):
                        raise ValueError("Unsupported content type")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 500_000:
                            raise ValueError("Page exceeds 500 KB decompressed size cap")
                    text = body.decode("utf-8", errors="replace")
                    parser = PageText()
                    parser.feed(text)
                    extracted = " ".join(part for part in parser.parts if part) if "html" in content_type else text
                    return ToolOutput(documents=[Evidence(url=url,
                        title=" ".join(parser.title_parts) or host, text=extracted[:30000])])
        raise ValueError("Too many redirects")
