from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class BaseAgent(ABC):
    """所有 Agent 的基类：统一名称、统一 run 方法、统一 trace 输出。"""

    name = "BaseAgent"

    def trace(self, input_summary: dict[str, Any], output_summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": self.name,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "input": input_summary,
            "output": output_summary,
        }

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError
