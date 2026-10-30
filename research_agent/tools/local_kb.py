import json
from ..safety import terms
from ..schemas import Evidence, ToolInput, ToolOutput
from .base import Tool


class LocalKB(Tool):
    name = "local_kb"

    async def execute(self, request: ToolInput) -> ToolOutput:
        documents = []
        query = terms(request.query)
        for path in sorted(self.settings.data_dir.glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            overlap = len(query & terms(document["title"] + " " + document["text"]))
            if overlap:
                documents.append((overlap, Evidence(**document, origin="local")))
        documents.sort(key=lambda row: (-row[0], row[1].url))
        return ToolOutput(documents=[doc for _, doc in documents[:request.limit]])
