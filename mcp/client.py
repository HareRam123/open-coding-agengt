

from enum import Enum
import os
from zipfile import Path

from config.config import MCPServerConfig
from fastmcp import Client 

class MCPServerStatus(str,Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class MCPClient:
    def __init__(self, name:str , 
                 config: MCPServerConfig,
                 cwd: Path | None = None) -> None:
        self.name = name
        self.cwd = cwd or Path(os.getcwd())
        self.config = config
        self.status = MCPServerStatus.DISCONNECTED
        self._client: Client | None = None

