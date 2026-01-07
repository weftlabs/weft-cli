"""Utility functions for feature state management."""

from pathlib import Path

from weft.config.runtime import WeftRuntime
from weft.state.feature_state import FeatureState, FeatureStatus


def get_state_file(feature_name: str) -> Path:
    runtime = WeftRuntime()
    return runtime.base_dir / "features" / feature_name / "state.yaml"


def get_feature_state(feature_name: str) -> FeatureState:
    """Creates initial state if file doesn't exist."""
    state_file = get_state_file(feature_name)
    if not state_file.exists():
        # Feature exists but no state file - create default
        state = FeatureState.create_initial(feature_name)
        state.save(state_file)
        return state
    return FeatureState.load(state_file)


def list_features_by_state(
    status: FeatureStatus | None = None,
) -> list[FeatureState]:
    runtime = WeftRuntime()
    features_dir = runtime.base_dir / "features"

    if not features_dir.exists():
        return []

    states = []
    for feature_dir in features_dir.iterdir():
        if not feature_dir.is_dir():
            continue

        state_file = feature_dir / "state.yaml"
        if not state_file.exists():
            continue

        try:
            state = FeatureState.load(state_file)
            if status is None or state.status == status:
                states.append(state)
        except Exception:
            # Skip invalid state files
            continue

    return states
