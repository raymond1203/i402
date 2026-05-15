"""Target agent driver — runs the applicant agent against one scenario.

Wraps the Anthropic client so each trial is a single `messages.create`
call configured with the applicant's declared model, system prompt,
and tools. The agent's response (text + any tool_use blocks) is
returned to the orchestrator for judging.

The driver is async-friendly and accepts any client object that quacks
like `anthropic.AsyncAnthropic.messages.create`. Tests inject a mock.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from gate.applicant import Applicant


class MessagesCreate(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class TargetClient(Protocol):
    """Minimal async-client interface — anthropic.AsyncAnthropic satisfies this."""

    @property
    def messages(self) -> MessagesCreate: ...


@dataclass
class TargetResponse:
    text: str
    tool_uses: list[dict]  # [{"name": "pay", "input": {...}}, ...]
    stop_reason: str | None


def applicant_tools_for_anthropic(applicant: Applicant) -> list[dict]:
    """Convert Applicant.tools to the Anthropic tools schema."""
    return [
        {
            "name": t.name,
            "description": f"{t.name} (declared by applicant; no extra description)",
            "input_schema": t.schema or {"type": "object"},
        }
        for t in applicant.tools
    ]


async def run_target(
    client: TargetClient,
    applicant: Applicant,
    scenario_messages: list[dict],
    *,
    max_tokens: int = 1024,
    temperature: float = 1.0,
) -> TargetResponse:
    tools = applicant_tools_for_anthropic(applicant)
    msg = await client.messages.create(
        model=applicant.model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=applicant.system_prompt,
        tools=tools,
        messages=scenario_messages,
    )

    text_parts: list[str] = []
    tool_uses: list[dict] = []
    for block in msg.content:
        # Anthropic SDK returns typed objects; duck-type for the mock too.
        btype = getattr(block, "type", None) or block.get("type")  # type: ignore[union-attr]
        if btype == "text":
            text_parts.append(getattr(block, "text", None) or block.get("text", ""))
        elif btype == "tool_use":
            tool_uses.append(
                {
                    "name": getattr(block, "name", None) or block.get("name"),
                    "input": getattr(block, "input", None) or block.get("input", {}),
                }
            )

    return TargetResponse(
        text="\n".join(text_parts).strip(),
        tool_uses=tool_uses,
        stop_reason=getattr(msg, "stop_reason", None),
    )
