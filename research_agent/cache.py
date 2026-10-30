import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from .schemas import ToolOutput


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class Cache:
    def __init__(self, root: Path, ttl: int, enabled: bool = True):
        self.root, self.ttl, self.enabled = root / ".cache", ttl, enabled

    def path(self, key: str) -> Path:
        return self.root / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    def get(self, key: str) -> ToolOutput | None:
        if not self.enabled:
            return None
        try:
            row = json.loads(self.path(key).read_text(encoding="utf-8"))
            if time.time() - row["created"] <= self.ttl:
                return ToolOutput.model_validate(row["value"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def put(self, key: str, value: ToolOutput):
        if self.enabled and value.documents and not value.warnings:
            atomic_write(self.path(key), json.dumps({"created": time.time(),
                         "value": value.model_dump(mode="json")}))
