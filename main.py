import asyncio
import os
from typing import Any
import click

from dotenv import load_dotenv

from LLMClient import LLMClient
from agent.agent import Agent
from agent.event import AgentEventType


load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

class CLI:
    
    def __init__(self, api_key: str, base_url: str):
        self.agent: Agent | None = None
        self.api_key = api_key
        self.base_url = base_url

    async def run_single(self, messages: str) -> None:
        async with Agent(api_key=self.api_key, base_url=self.base_url) as agent:
            self.agent = agent
            await self._process_message(messages)

    async def _process_message(self, messages: str) -> str |  None:
        if not self.agent:
            raise RuntimeError("Agent is not initialized. Call run_single first.")
        
        async for event in self.agent.run(messages):
            if event.type == AgentEventType.TEXT_DELTA:
                print(event.data.get("content", ""), end="", flush=True)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                print("\n---\nFinal Response:", event.data.get("content", ""))
            elif event.type == AgentEventType.AGENT_ERROR:
                print("\nError:", event.data.get("error", "Unknown error"))


async def run(messages: list[dict[str, Any]]) -> None:
    client = LLMClient(api_key=API_KEY, base_url=BASE_URL)
    async for event in client.chat_completion(
        messages=messages,
        stream=True
    ):
        print(event)

@click.command()
@click.argument("prompt", required=False)
def main(prompt: str) -> None:
    cli = CLI(api_key=API_KEY, base_url=BASE_URL)
    print("Starting the agent...", prompt)
    if prompt:
        asyncio.run(cli.run_single(prompt))


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