
import asyncio
import inspect
import os
from typing import Any, AsyncGenerator

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from response import StreamEventType, StreamEvent, TextDelta, TokenUsage, ToolCallDelta, ToolCall, parse_tool_call_arguments

from dotenv import load_dotenv
import openai


load_dotenv()


class LLMClient:
    def __init__(self, api_key, base_url):
        self._client: AsyncOpenAI | None = None
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = 3

    async def get_client(self):
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client


    def _build_tools(self, tools: list[dict[str, Any]]):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {
                            "type": "object",
                            "properties": {},
                        },
                    ),
                },
            }
            for tool in tools
        ]


    async def chat_completion(self, 
                              messages: list[dict[str,Any]],
                              tools: list[dict[str, Any]] | None = None,
                              stream: bool = False
                              ) -> AsyncGenerator[StreamEvent, None] | None:
            client = await self.get_client()
            kwargs = {
                "model": "openai/gpt-4o-mini",
                "messages": messages,
                "stream": stream,
            }

            if tools:
                kwargs["tools"] = self._build_tools(tools)
                kwargs["tool_choice"] = "auto"

            for attempt in range(self.max_retries + 1):
                try:
                    if stream:
                        async for event in self._stream_response( client,kwargs):
                            yield event
                    else:
                        event = await self._non_stream_response( client, kwargs)
                        yield event

                    return  # Exit the function if successful

                except (APIConnectionError, APIError, RateLimitError) as e:
                    if attempt < self.max_retries:
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        yield StreamEvent(
                            type=StreamEventType.ERROR,
                            error=str(e),
                        )
                        return  # Exit after yielding the error event
                    

    async def _non_stream_response(self, 
                                   client: AsyncOpenAI, 
                                   kwargs: dict[str, Any])-> StreamEvent:
        
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        text_delta = None
        usage = None
        if message.content:
            text_delta = TextDelta(content=message.content)

        
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        call_id=tc.id,
                        name=tc.function.name,
                        arguments=parse_tool_call_arguments(tc.function.arguments),
                    )
                )

        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=response.usage.prompt_tokens_details.cached_tokens,
            )

        return StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            finish_reason=choice.finish_reason,
            usage=usage,
        )

    async def _stream_response(self, 
                                   client: AsyncOpenAI, 
                                   kwargs: dict[str, Any]) -> AsyncGenerator[StreamEvent, None]:
        
        response = await client.chat.completions.create(**kwargs)
        finish_reason = None
        usage = None
        tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in response:
            if hasattr(chunk,"usage") and chunk.usage:
                
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens,
                )

            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            text_delta = None
            if choice.delta and choice.delta.content:
                text_delta = TextDelta(content=choice.delta.content)
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=text_delta,
                )

            #print(choice.delta.tool_calls) 

            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index

                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }

                        if tool_call_delta.function and tool_call_delta.function.name:
                            tool_calls[idx]["name"] = tool_call_delta.function.name
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL_START,
                                tool_call_delta=ToolCallDelta(
                                    call_id=tool_calls[idx]["id"],
                                    name=tool_call_delta.function.name,
                                ),
                            )

                    if tool_call_delta.function and tool_call_delta.function.arguments:
                        tool_calls[idx]["arguments"] += tool_call_delta.function.arguments
                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_DELTA,
                            tool_call_delta=ToolCallDelta(
                                call_id=tool_calls[idx]["id"],
                                name=tool_call_delta.function.name,
                                arguments_delta=tool_call_delta.function.arguments,
                            ),
                        )

        for idx, tc in tool_calls.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
                    call_id=tc["id"],
                    name=tc["name"],
                    arguments=parse_tool_call_arguments(tc["arguments"]),
                ),
            )
            
        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )


    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None