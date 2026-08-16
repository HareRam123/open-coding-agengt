


from __future__ import annotations
import json
from pathlib import Path
from agent.session import Session
from typing import AsyncGenerator

from agent.event import AgentEvent, AgentEventType
from response import StreamEventType, ToolCall, ToolResultMessage


class Agent:
    def __init__(self, config):
        self.session :Session | None = Session(config=config)
        self.config = self.session.config
        

    async def run(self, prompt: str):
        final_response: str | None = None
        yield AgentEvent.agent_start(message="Agent started")
        self.session.context_manager.add_user_message(content=prompt)
        async for event in self._agentic_loop(prompt):
            yield event
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(response=final_response, usage=None)

    async def _agentic_loop(self, prompt: str) -> AsyncGenerator[AgentEvent, None]:
        max_turns = self.config.max_turns

        for turn_num in range(max_turns):
            self.session.increment_turn()
            response_text = ""

            tool_schemas = self.session.tool_registry.get_schemas()
            messages = self.session.context_manager.get_messages()
            tool_calls: list[ToolCall] = []
            tool_call_results: list[ToolResultMessage] = []

            async for event in self.session.client.chat_completion(
                self.session.context_manager.get_messages(),
                tools=tool_schemas if tool_schemas else None,
                stream=True,
            ):
                if event.type == StreamEventType.TEXT_DELTA:
                    if event.text_delta:
                        content = event.text_delta.content
                        response_text += content
                        yield AgentEvent.text_delta(content)
                elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                    if event.tool_call:
                        tool_calls.append(event.tool_call)
                elif event.type == StreamEventType.ERROR:
                    yield AgentEvent.agent_error(
                        event.error or "Unknown error occurred.",
                    )
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage


        
            self.session.context_manager.add_assistant_message(
                response_text or None,
                (
                    [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in tool_calls
                    ]
                    if tool_calls
                    else None
                ),
            )
            
            if response_text:
                yield AgentEvent.text_complete(content=response_text)

            if not tool_calls:
                break

            for tool_call in tool_calls:
                yield AgentEvent.tool_call_start(call_id=tool_call.call_id, 
                                                name=tool_call.name or "", 
                                                arguments=tool_call.arguments)
                
                result = await self.session.tool_registry.invoke(name=tool_call.name or "",
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
                self.session.context_manager.add_tool_result(
                    tool_call_id=tool_result.tool_call_id,
                    content=tool_result.content,
                )
                
    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        if self.session and self.session.client :
            await self.session.client.close()

            self.session = None


