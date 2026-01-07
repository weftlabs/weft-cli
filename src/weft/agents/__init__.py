"""AI agents for the workflow system.

Agents are now config-driven and loaded dynamically from config.yaml files.
No subclassing needed - all agents use BaseSpecAgent with different configs.
"""

from weft.agents.base_spec_agent import BaseSpecAgent
from weft.agents.discovery import discover_agent_configs, get_agent_execution_order

__all__ = [
    "BaseSpecAgent",
    "discover_agent_configs",
    "get_agent_execution_order",
]
