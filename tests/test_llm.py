import asyncio
from types import SimpleNamespace
import httpx
import pytest
from pydantic import ValidationError
from research_agent.llm import LLM
from research_agent.planner import fallback_plan
from research_agent.schemas import Plan


class Responses:
    def __init__(self, sequence):
        self.sequence, self.calls = sequence, []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        value = self.sequence.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def client(llm, sequence):
    responses = Responses(sequence)
    llm.client = SimpleNamespace(responses=responses)
    llm.settings.mock = False
    return responses


def response(plan):
    return SimpleNamespace(output_parsed=plan,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=20))


def test_sdk_schema_repair_and_accounting(settings, context):
    llm = LLM(settings, context[0])
    plan = fallback_plan("vector databases", 8)
    sdk = client(llm, [ValueError("invalid schema"), response(plan)])
    actual = asyncio.run(llm.generate(Plan, "Plan research", {"question": "x"}, plan))
    assert actual == plan and len(sdk.calls) == 2
    assert sdk.calls[0]["text_format"] is Plan
    assert len(sdk.calls[1]["input"]) == 3
    assert llm.tokens == {"input": 100, "output": 20}
    assert llm.cost() is None
    llm.settings.input_price, llm.settings.output_price = 1, 2
    assert llm.cost() == pytest.approx(0.00014)


def test_sdk_refusal_repair_then_failure(settings, context):
    llm = LLM(settings, context[0])
    plan = fallback_plan("vector databases", 8)
    sdk = client(llm, [SimpleNamespace(output_parsed=None, usage=None)] * 2)
    with pytest.raises(ValueError):
        asyncio.run(llm.generate(Plan, "Plan", {}, plan))
    assert len(sdk.calls) == 2


def test_sdk_transient_timeout_retry(settings, context):
    llm = LLM(settings, context[0])
    plan = fallback_plan("vector databases", 8)
    sdk = client(llm, [httpx.ReadTimeout("timeout"), response(plan)])
    assert asyncio.run(llm.generate(Plan, "Plan", {}, plan)) == plan
    assert len(sdk.calls) == 2


def test_missing_key_never_uses_fake_live_response(settings, context):
    llm = LLM(settings, context[0])
    settings.mock = False
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        asyncio.run(llm.generate(Plan, "Plan", {}, fallback_plan("question", 8)))
