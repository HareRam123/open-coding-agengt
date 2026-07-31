import asyncio
import os
from typing import Any
import click

from dotenv import load_dotenv

from LLMClient import LLMClient


load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

async def run(messages: list[dict[str, Any]]) -> None:
    client = LLMClient(api_key=API_KEY, base_url=BASE_URL)
    async for event in client.chat_completion(
        messages=messages,
        stream=True
    ):
        print(event)

@click.command()
@click.option('--message', prompt='Enter your message', help='The message to send to the LLM.')
def main(message: str) -> None:
    messages = [{"role": "user", "content": message}]
    asyncio.run(run(messages))

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