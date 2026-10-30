import asyncio
import json
import random
from abc import ABC, abstractmethod
from pydantic import ValidationError
from ..cache import Cache
from ..config import Settings
from ..schemas import ToolInput, ToolOutput
from ..tracing import Trace


class Tool(ABC):
    name: str
    cacheable = False

    def __init__(self, settings: Settings, trace: Trace, cache: Cache):
        self.settings, self.trace, self.cache = settings, trace, cache

    @abstractmethod
    async def execute(self, request: ToolInput) -> ToolOutput | dict | str:
        raise NotImplementedError

    async def run(self, request: ToolInput) -> ToolOutput:
        request = ToolInput.model_validate(request.model_dump())
        namespace = f"mock:{self.settings.scenario}" if self.settings.mock else "live"
        key = f"v1:{namespace}:{self.name}:{request.model_dump_json()}"
        if self.cacheable and (cached := self.cache.get(key)) is not None:
            self.trace.event("tool", tool=self.name, status="cache_hit", duration_ms=0,
                             retries=0, input_summary={"query_chars": len(request.query)})
            return cached
        for attempt in range(2):
            try:
                with self.trace.span("tool", tool=self.name, retries=attempt,
                                     input_summary={"query_chars": len(request.query),
                                                    "has_url": request.url is not None}):
                    async with asyncio.timeout(self.settings.tool_timeout):
                        raw = await self.execute(request)
                        result = (ToolOutput.model_validate_json(raw) if isinstance(raw, str)
                                  else ToolOutput.model_validate(raw))
                if self.cacheable:
                    self.cache.put(key, result)
                return result
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.trace.event("tool_error", tool=self.name, retries=attempt,
                                 error=type(exc).__name__)
                # One retry is also the repair opportunity for malformed provider output.
                if isinstance(exc, ValueError) and not isinstance(exc, (ValidationError, json.JSONDecodeError)):
                    break
                if attempt == 0:
                    await asyncio.sleep(0.05 * 2**attempt + random.uniform(0, 0.03))
        return ToolOutput(warnings=[f"{self.name} failed after bounded attempts; see trace"])
