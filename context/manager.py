from typing import Any
from config.config import Config
from dataclasses import dataclass, field
from typing import Any

from config.config import Config
from prompts.system import get_system_prompt

from tools.base import Tool
from utils.text import count_tokens


@dataclass
class MessageItem:
    role: str
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    token_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"role": self.role, "content": self.content}

        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        if self.tool_calls:
            result["tool_calls"] = self.tool_calls

        return result


class ContextManager:
    def __init__(self, config: Config | None = None, user_memory: str | None = None, tools: list[Tool] | None = None):
        self._system_prompt = get_system_prompt(config, user_memory=user_memory, tools=tools)
        self._model_name = config.model_name if config else "gpt-4"
        self._messages: list[MessageItem] = []

    def add_user_message(self, content: str) -> None:
        item = MessageItem(
            role="user",
            content=content,
            token_count=count_tokens(content, model=self._model_name),
        )
        self._messages.append(item)

    def add_assistant_message(
        self,
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        item = MessageItem(
            role="assistant",
            content=content or "",
            tool_calls=tool_calls or [],
            token_count=count_tokens(content or "", model=self._model_name),
        )
        self._messages.append(item)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        item = MessageItem(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            token_count=count_tokens(content, self._model_name),
        )

        self._messages.append(item)

    def get_messages(self) -> list[dict[str, Any]]:
        messages = []

        if self._system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self._system_prompt,
                }
            )

        for item in self._messages:
            messages.append(item.to_dict())

        return messages

