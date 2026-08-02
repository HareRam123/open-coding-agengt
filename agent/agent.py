


from __future__ import annotations
from os import name
from tools.registry import create_default_registry
from typing import AsyncGenerator

from LLMClient import LLMClient
from agent.event import AgentEvent, AgentEventType
from response import StreamEventType
from context.manager import ContextManager


class Agent:
    def __init__(self, api_key: str, base_url: str):
        self.client = LLMClient(api_key=api_key, base_url=base_url)
        self.context_manager = ContextManager()  # Initialize context manager if needed
        self.tool_registry = create_default_registry()  

    async def run(self, prompt: str):
        final_response: str | None = None
        yield AgentEvent.agent_start(message="Agent started")
        self.context_manager.add_user_message(content=prompt)
        async for event in self._agentic_loop(prompt):
            yield event
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(response=final_response, usage=None)

    async def _agentic_loop(self, prompt: str) -> AsyncGenerator[AgentEvent, None]:
        
        response_text = ""
        tool_schemas = self.tool_registry.get_schemas()
        messages = self.context_manager.get_messages()

        import json
        #print(json.dumps(messages, indent=2))
        #print(json.dumps(tool_schemas, indent=2))

        
        async for event in self.client.chat_completion(messages=messages, 
                                                       tools=tool_schemas if tool_schemas else None,
                                                       stream=True):
            if event.type == StreamEventType.TEXT_DELTA:
                content = event.text_delta.content if event.text_delta else ""
                response_text += content
                yield AgentEvent.text_delta(content=content)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(error=event.error or "Unknown error")

            print(event)

        self.context_manager.add_assistant_message(content=response_text or None)
        if response_text:
            yield AgentEvent.text_complete(content=response_text)

    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            


