from .llm import LLM
from .schemas import Plan, Step


def fallback_plan(question: str, max_steps: int) -> Plan:
    conceptual = any(word in question.lower() for word in ("memory", "architecture", "pros", "cons"))
    tools = ["local_kb", "web_search"] if conceptual else ["web_search", "local_kb"]
    return Plan(steps=[Step(sub_question=question, tool=tool,
                reasoning="Curated conceptual context" if tool == "local_kb" else
                          "Discover external sources and current primary references") for tool in tools],
                success_criteria=["At least three relevant independent sources", "Cited, qualified findings"],
                max_steps=max_steps)


async def create_plan(question: str, llm: LLM) -> Plan:
    fallback = fallback_plan(question, llm.settings.max_steps)
    try:
        plan = await llm.generate(Plan,
            "Plan bounded research, with specific sub-questions. Tools: web_search discovers URLs; "
            "local_kb provides conceptual offline context; fetch_page is only for a URL supplied "
            "by the user. Executor fetches promising search URLs automatically. Use local_kb for "
            "concept questions and web_search for comparisons or current facts. Never invent URLs.",
            {"question": question, "step_budget": llm.settings.max_steps}, fallback)
        plan.max_steps = min(plan.max_steps, llm.settings.max_steps)
        plan.steps = plan.steps[:plan.max_steps]
        return plan
    except Exception as exc:
        llm.trace.event("planner_fallback", error=type(exc).__name__)
        return fallback
