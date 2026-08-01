from __future__ import annotations
import abc
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ValidationError
from pydantic_core import ValidationError
from pydantic.json_schema import model_json_schema

class ToolKind(str, Enum):
   READ = "read"
   WRITE = "write"
   SHELL = "shell"
   NETWORK = "network"
   MEMORY = "memory"
   MCP = "mcp"

@dataclass
class ToolResult:
    success: bool
    output: str 
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    
@dataclass
class ToolInvocation:
    cwd: Path | None
    params: dict[str, Any]


@dataclass
class ToolConfirmation:
    tool_name: str
    params: dict[str, Any]
    description: str


    

class Tool(abc.ABC):
    name:str = "base_tool"
    description:str = "This is a base tool. It should be subclassed to create specific tools."
    kind:ToolKind = ToolKind.READ
    
    def __init__(self):
        pass

    @property
    def schema(self) -> dict[str, Any] | type[BaseModel]:
        raise NotImplementedError("Subclasses must implement the schema property.")

    @abc.abstractmethod
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """
        Execute the tool with the given invocation.

        Args:
            invocation (ToolInvocation): The invocation data for the tool.

        Returns:
            ToolResult: The result of the tool execution.
        """
        raise NotImplementedError("Subclasses must implement the execute method.")

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        schema = self.schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                schema(**params)
            except ValidationError as e:
                errors = []
                for error in e.errors():
                    field = ".".join(str(x) for x in error.get("loc", []))
                    msg = error.get("msg", "Validation error")
                    errors.append(f"Parameter '{field}': {msg}")

                return errors
            except Exception as e:
                return [str(e)]

        return []

    def is_mutating(self) -> bool:
        return self.kind in {ToolKind.WRITE, ToolKind.SHELL, ToolKind.NETWORK, ToolKind.MCP}

    
    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        if not self.is_mutating(invocation.params):
            return None

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Execute {self.name}",
        )

    def to_openai_schema(self) -> dict[str, Any]:
        schema = self.schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            json_schema =  model_json_schema(schema, mode="serialization")  # Use Pydantic's built-in method to get the JSON schema
        elif isinstance(schema, dict):
            return schema
        else:
            raise TypeError("Schema must be a Pydantic model or a dictionary.")

    def to_openai_schema(self) -> dict[str, Any]:
        schema = self.schema

        if isinstance(schema, type) and issubclass(schema, BaseModel):

            json_schema = model_json_schema(schema, mode="serialization")

            return {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": json_schema.get("properties", {}),
                    "required": json_schema.get("required", []),
                },
            }

        if isinstance(schema, dict):
            result = {
                "name": self.name,
                "description": self.description,
            }

            if "parameters" in schema:
                result["parameters"] = schema["parameters"]
            else:
                result["parameters"] = schema

            return result

        raise ValueError(f"Invalid schema type for tool {self.name}: {type(schema)}")