from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolDefinition:
    tool_name: str
    description: str
    risk_level: str
    enabled: bool
    callable_function: Callable