import asyncio
from logging import config
import os
import sys
from typing import Any
import click

from dotenv import load_dotenv

from LLMClient import LLMClient
from agent.agent import Agent
from agent.event import AgentEventType
from ui.tui import TUI, get_console


load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

console = get_console()

class CLI:
    
    def __init__(self, api_key: str, base_url: str):
        self.agent: Agent | None = None
        self.api_key = api_key
        self.base_url = base_url
        self.tui = TUI(console)

    async def run_single(self, messages: str) -> str | None:
        async with Agent(api_key=self.api_key, base_url=self.base_url) as agent:
            self.agent = agent
            return await self._process_message(messages)

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool_kind = None
        tool = self.agent.tool_registry.get(tool_name)
        if not tool:
            tool_kind = None

        tool_kind = tool.kind.value

        return tool_kind


    async def _process_message(self, messages: str) -> str |  None:
        if not self.agent:
            raise RuntimeError("Agent is not initialized. Call run_single first.")

        assistant_streaming = False
        final_response: str | None = None
        
        
        async for event in self.agent.run(messages):
            #print("main event", event)
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)

            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
                    
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]Error: {error}[/error]")
                
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {}),
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error"),
                    event.data.get("metadata"),
                    event.data.get("diff"),
                    event.data.get("truncated", False),
                    event.data.get("exit_code"),
                )

        return final_response


async def run(messages: list[dict[str, Any]]) -> None:
    client = LLMClient(api_key=API_KEY, base_url=BASE_URL)
    async for event in client.chat_completion(
        messages=messages,
        stream=True
    ):
        pass


@click.command()
@click.argument("prompt", required=False)
def main(prompt: str) -> None:
    cli = CLI(api_key=API_KEY, base_url=BASE_URL)
    print("Starting the agent...", prompt)
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)


# async def main() -> None:
#     if not API_KEY:
#         raise RuntimeError("OPENROUTER_API_KEY not found in .env")

#     client = LLMClient(api_key=API_KEY, base_url=BASE_URL)

#     async for event in client.chat_completion(
#         messages=[{"role": "user", "content": "Hello! Tell me a joke."}],
#         stream=True
#     ):
#         print(event)

#     # print(response.choices[0].message.content)
#     # print(response)


if __name__ == "__main__":
    main()