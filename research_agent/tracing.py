import json
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from .schemas import now


class Trace:
    def __init__(self, root: Path):
        self.run_id = uuid4().hex
        self.path = root / "runs" / f"{self.run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, name: str, **fields):
        row = {"timestamp": now().isoformat(), "run_id": self.run_id, "name": name, **fields}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, default=str) + "\n")

    @contextmanager
    def span(self, name: str, **fields):
        started = time.perf_counter()
        status = "ok"
        try:
            yield
        except BaseException as exc:
            status = type(exc).__name__
            raise
        finally:
            self.event(name, status=status, duration_ms=round((time.perf_counter()-started)*1000, 2),
                       **fields)
