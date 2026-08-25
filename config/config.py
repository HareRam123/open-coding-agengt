from __future__ import annotations
import os

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

class ModelConfig(BaseModel):
    name: str = "openai/gpt-4o-mini"
    temperature: float = Field(default=1, ge=0.0, le=2.0)
    context_window: int = 256_000

class MCPServerConfig(BaseModel):
    enabled: bool = True
    startup_timeout_sec: float = 10

    #stdio transport configuration

    command: str | None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None

    #http transport configuration/ sse
    url: str | None = None

    
    @model_validator(mode="after")
    def validate_transport(self) -> MCPServerConfig:
        has_command = self.command is not None
        has_url = self.url is not None

        if not has_command and not has_url:
            raise ValueError(
                "MCP Server must have either 'command' (stdio) or 'url' (http/sse)"
            )

        if has_command and has_url:
            raise ValueError(
                "MCP Server cannot have both 'command' (stdio) and 'url' (http/sse)"
            )

        return self




class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)
    max_turns: int = 100
    max_tool_output_tokens: int = 10_000

    #mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict, description="MCP server configurations")

    allowed_tools: list[str] | None = Field(default=None, description="List of allowed tools for the agent. If None, all tools are allowed.")

    developer_instructions: str | None = None
    user_instructions: str | None = None

    debug: bool = False

    @property
    def api_key(self) -> str | None:
        return os.environ.get("OPENROUTER_API_KEY")

    @property
    def base_url(self) -> str | None:
        return os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    @property
    def model_name(self) -> str:
        return self.model.name

    
    @model_name.setter
    def model_name(self, value: str) -> None:
        self.model.name = value

    
    @property
    def temperature(self) -> float:
        return self.model.temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        self.model.temperature = value

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.api_key:
            errors.append("No API key found. Set OPENROUTER_API_KEY environment variable")

        if not self.cwd.exists():
            errors.append(f"Working directory does not exist: {self.cwd}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
