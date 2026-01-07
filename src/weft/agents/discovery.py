"""Agent discovery and ordering."""

from pathlib import Path
from typing import Any

import yaml

from weft.constants import AGENT_STAGES


def discover_agent_configs() -> list[dict]:
    agents_dir = Path(__file__).parent
    configs = []

    # Scan for subdirectories with config.yaml
    for item in agents_dir.iterdir():
        if not item.is_dir():
            continue
        if item.name.startswith("_"):  # Skip __pycache__, etc.
            continue

        config_path = item / "config.yaml"
        if not config_path.exists():
            continue

        # Load config
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Add agent directory path to config
        config["agent_dir"] = item

        configs.append(config)

    return configs


def get_agent_execution_order() -> list[dict]:
    """Sorted by stage order from AGENT_STAGES, then order_in_stage."""
    configs = discover_agent_configs()

    # Validate stages
    for config in configs:
        stage = config.get("stage")
        if not stage:
            raise ValueError(f"Agent {config.get('agent_name')} missing 'stage' in config")
        if stage not in AGENT_STAGES:
            raise ValueError(f"Agent {config.get('agent_name')} has invalid stage: {stage}")

    # Group by stage
    stages_dict: dict[str, list[dict[str, Any]]] = {}
    for config in configs:
        stage = config["stage"]
        if stage not in stages_dict:
            stages_dict[stage] = []
        stages_dict[stage].append(config)

    # Sort within each stage by order_in_stage
    for stage_agents in stages_dict.values():
        stage_agents.sort(key=lambda c: c.get("order_in_stage", 0))

    # Build final order from stage sequence
    ordered_configs = []
    for stage_name in AGENT_STAGES:
        if stage_name in stages_dict:
            ordered_configs.extend(stages_dict[stage_name])

    return ordered_configs
