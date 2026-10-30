import pytest
from pydantic import ValidationError
from research_agent.schemas import Finding, Plan, ToolInput, ToolOutput


def test_tool_schema_rejects_malformed_and_extra_fields():
    for raw in ({"documents": "wrong"}, {"documents": [], "surprise": True}):
        with pytest.raises(ValidationError):
            ToolOutput.model_validate(raw)


def test_plan_and_finding_enums():
    with pytest.raises(ValidationError):
        Plan(steps=[], success_criteria=[], max_steps=100)
    with pytest.raises(ValidationError):
        Finding(claim="x", evidence_source_ids=[], support="certain")
    with pytest.raises(ValidationError):
        ToolInput(query="", limit=99)
