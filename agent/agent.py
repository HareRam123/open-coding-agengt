


from __future__ import annotations
from os import name
from typing import AsyncGenerator

from LLMClient import LLMClient
from agent.event import AgentEvent, AgentEventType
from response import StreamEventType


class Agent:
    def __init__(self, api_key: str, base_url: str):
        self.client = LLMClient(api_key=api_key, base_url=base_url)

    async def run(self, messages: list[dict[str, str]]):
        final_response: str | None = None
        yield AgentEvent.agent_start(message="Agent started")
        async for event in self._agentic_loop():
            yield event
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(response=final_response, usage=None)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        messages = [{"role": "user", "content": "Hello! Tell me a joke."}]
        response_text = ""
        async for event in self.client.chat_completion(messages=messages, stream=True):
            if event.type == StreamEventType.TEXT_DELTA:
                content = event.text_delta.content if event.text_delta else ""
                response_text += content
                yield AgentEvent.text_delta(content=content)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(error=event.error or "Unknown error")

        if response_text:
            yield AgentEvent.text_complete(content=response_text)

    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            


