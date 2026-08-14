


from __future__ import annotations
from pathlib import Path
from agent.session import Session
from typing import AsyncGenerator

from agent.event import AgentEvent, AgentEventType
from response import StreamEventType, ToolCall, ToolResultMessage


class Agent:
    def __init__(self, config):
        self.config = config
        self.session = Session(config=config)
        self.client = self.session.client
        self.context_manager = self.session.context_manager
        self.tool_registry = self.session.tool_registry
        

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
        tool_calls: list[ToolCall] = []
        tool_call_results: list[ToolResultMessage] = []

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
            elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                if event.tool_call:
                    tool_calls.append(event.tool_call)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(error=event.error or "Unknown error")

            #print(event)

        self.context_manager.add_assistant_message(content=response_text or None)
        if response_text:
            yield AgentEvent.text_complete(content=response_text)

        for tool_call in tool_calls:
            yield AgentEvent.tool_call_start(call_id=tool_call.call_id, 
                                             name=tool_call.name or "", 
                                             arguments=tool_call.arguments)
            
            result = await self.tool_registry.invoke(name=tool_call.name or "",
                                      params=tool_call.arguments,
                                      cwd=self.config.cwd,
                                      )
            yield AgentEvent.tool_call_complete(
                call_id=tool_call.call_id,
                name=tool_call.name or "",
                result=result,
            )

            tool_call_results.append(ToolResultMessage(
                tool_call_id=tool_call.call_id,
                content=result.to_model_output(),
                is_error=not result.success,
            ))

        for tool_result in tool_call_results:
            self.context_manager.add_tool_result(
                tool_call_id=tool_result.tool_call_id,
                content=tool_result.content,
            )
    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            


