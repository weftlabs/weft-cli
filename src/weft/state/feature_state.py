"""Feature state management models."""

from datetime import datetime
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class FeatureStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in-progress"
    READY = "ready"
    MERGE_CONFLICT = "merge-conflict"
    COMPLETED = "completed"
    DROPPED = "dropped"


class StateTransition(BaseModel):
    from_state: FeatureStatus | None = None
    to_state: FeatureStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: str | None = None


class FeatureState(BaseModel):
    feature_name: str
    status: FeatureStatus
    created_at: datetime
    last_activity: datetime = Field(default_factory=datetime.now)
    transitions: list[StateTransition] = Field(default_factory=list)
    merge_commit: str | None = None  # Set when completed
    merge_error: str | None = None  # Set when merge fails
    drop_reason: str | None = None  # Set when dropped

    @classmethod
    def load(cls, state_file: Path) -> "FeatureState":
        if not state_file.exists():
            raise FileNotFoundError(f"State file not found: {state_file}")

        with open(state_file) as f:
            data = yaml.safe_load(f)

        # Convert timestamp strings to datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_activity"] = datetime.fromisoformat(data["last_activity"])

        # Convert status string to enum
        data["status"] = FeatureStatus(data["status"])

        # Convert transition timestamps and status strings to enums
        for t in data.get("transitions", []):
            t["timestamp"] = datetime.fromisoformat(t["timestamp"])
            if t.get("from_state"):
                t["from_state"] = FeatureStatus(t["from_state"])
            t["to_state"] = FeatureStatus(t["to_state"])

        return cls(**data)

    def save(self, state_file: Path) -> None:
        state_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict with ISO format timestamps and enum values
        data = self.model_dump()
        data["created_at"] = self.created_at.isoformat()
        data["last_activity"] = self.last_activity.isoformat()
        data["status"] = self.status.value  # Convert enum to string

        # Convert transition timestamps and enum values
        for t in data["transitions"]:
            if isinstance(t["timestamp"], datetime):
                t["timestamp"] = t["timestamp"].isoformat()
            elif isinstance(t["timestamp"], str):
                # Already a string, ensure it's ISO format
                t["timestamp"] = datetime.fromisoformat(t["timestamp"]).isoformat()

            # Convert from_state and to_state enums to strings
            if t.get("from_state") and isinstance(t["from_state"], FeatureStatus):
                t["from_state"] = t["from_state"].value
            if isinstance(t["to_state"], FeatureStatus):
                t["to_state"] = t["to_state"].value

        with open(state_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def transition_to(self, new_status: FeatureStatus, reason: str | None = None) -> None:
        """Validates and records state transition."""
        # Skip if already in target state
        if self.status == new_status:
            return

        # Validate transition
        if not self._is_valid_transition(new_status):
            raise ValueError(f"Invalid state transition: {self.status} -> {new_status}")

        # Record transition
        transition = StateTransition(from_state=self.status, to_state=new_status, reason=reason)
        self.transitions.append(transition)

        # Update status
        self.status = new_status
        self.last_activity = datetime.now()

    def _is_valid_transition(self, new_status: FeatureStatus) -> bool:
        valid_transitions = {
            FeatureStatus.DRAFT: [FeatureStatus.IN_PROGRESS, FeatureStatus.DROPPED],
            FeatureStatus.IN_PROGRESS: [
                FeatureStatus.READY,
                FeatureStatus.DRAFT,
                FeatureStatus.DROPPED,
            ],
            FeatureStatus.READY: [
                FeatureStatus.COMPLETED,
                FeatureStatus.MERGE_CONFLICT,
                FeatureStatus.IN_PROGRESS,
                FeatureStatus.DROPPED,
            ],
            FeatureStatus.MERGE_CONFLICT: [
                FeatureStatus.COMPLETED,  # After resolving and retrying merge
                FeatureStatus.READY,  # Go back to ready to retry
                FeatureStatus.DROPPED,  # Give up
            ],
            FeatureStatus.COMPLETED: [],  # Terminal state
            FeatureStatus.DROPPED: [],  # Terminal state
        }

        return new_status in valid_transitions.get(self.status, [])

    @staticmethod
    def create_initial(feature_name: str) -> "FeatureState":
        now = datetime.now()
        return FeatureState(
            feature_name=feature_name,
            status=FeatureStatus.DRAFT,
            created_at=now,
            last_activity=now,
            transitions=[
                StateTransition(
                    from_state=None,
                    to_state=FeatureStatus.DRAFT,
                    timestamp=now,
                    reason="Feature created",
                )
            ],
        )


def load_feature_state(feature_name: str) -> FeatureState:
    """Load feature state from file."""
    from weft.state.utils import get_state_file

    state_file = get_state_file(feature_name)
    return FeatureState.load(state_file)
