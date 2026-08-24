from __future__ import annotations

from typing import Any

from agent.agent import Agent
from agent.event import AgentEventType


async def run_prompt(agent: Agent, prompt: str) -> dict[str, Any]:
    text_chunks: list[str] = []
    tool_events: list[dict[str, Any]] = []
    errors: list[str] = []

    async for event in agent.run(prompt):
        if event.type == AgentEventType.TEXT_DELTA:
            text_chunks.append(event.data.get("content", ""))
        elif event.type == AgentEventType.TEXT_COMPLETE:
            # Prefer TEXT_COMPLETE payload if available.
            complete = event.data.get("content")
            if isinstance(complete, str):
                text_chunks = [complete]
        elif event.type == AgentEventType.TOOL_CALL_START:
            tool_events.append(
                {
                    "phase": "start",
                    "call_id": event.data.get("call_id", ""),
                    "name": event.data.get("name", "unknown"),
                    "arguments": event.data.get("arguments", {}),
                }
            )
        elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
            tool_events.append(
                {
                    "phase": "complete",
                    "call_id": event.data.get("call_id", ""),
                    "name": event.data.get("name", "unknown"),
                    "success": event.data.get("success", False),
                    "output": event.data.get("output", ""),
                    "error": event.data.get("error"),
                    "metadata": event.data.get("metadata", {}),
                    "diff": event.data.get("diff"),
                    "truncated": event.data.get("truncated", False),
                    "exit_code": event.data.get("exit_code"),
                }
            )
        elif event.type == AgentEventType.AGENT_ERROR:
            errors.append(event.data.get("error", "Unknown agent error"))

    return {
        "response": "".join(text_chunks).strip(),
        "tool_events": tool_events,
        "errors": errors,
    }
