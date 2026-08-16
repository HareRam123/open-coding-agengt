
from datetime import datetime
import uuid

from LLMClient import LLMClient
from config.config import Config
from context.manager import ContextManager
from tools.registry import create_default_registry


class Session:
    def __init__(self, config: Config):
        self.config = config
        self.client = LLMClient(config=config)
        self.tool_registry = create_default_registry(config)
        self.context_manager = ContextManager(config=config)
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        self.turn_count = 0


    def increment_turn(self) -> int:
        self.turn_count += 1
        self.updated_at = datetime.now()

        return self.turn_count