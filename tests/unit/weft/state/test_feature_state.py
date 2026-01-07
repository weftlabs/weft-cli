"""Unit tests for feature state management."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from weft.state.feature_state import FeatureState, FeatureStatus, StateTransition
from weft.state.utils import get_feature_state, get_state_file, list_features_by_state


class TestFeatureStatus:
    """Tests for FeatureStatus enum."""

    def test_all_statuses_defined(self):
        """Test that all expected statuses are defined."""
        assert FeatureStatus.DRAFT == "draft"
        assert FeatureStatus.IN_PROGRESS == "in-progress"
        assert FeatureStatus.READY == "ready"
        assert FeatureStatus.MERGE_CONFLICT == "merge-conflict"
        assert FeatureStatus.COMPLETED == "completed"
        assert FeatureStatus.DROPPED == "dropped"

    def test_status_values_are_strings(self):
        """Test that status values are strings."""
        for status in FeatureStatus:
            assert isinstance(status.value, str)


class TestStateTransition:
    """Tests for StateTransition model."""

    def test_create_transition_with_all_fields(self):
        """Test creating a transition with all fields."""
        now = datetime.now()
        transition = StateTransition(
            from_state=FeatureStatus.DRAFT,
            to_state=FeatureStatus.IN_PROGRESS,
            timestamp=now,
            reason="Testing transition",
        )

        assert transition.from_state == FeatureStatus.DRAFT
        assert transition.to_state == FeatureStatus.IN_PROGRESS
        assert transition.timestamp == now
        assert transition.reason == "Testing transition"

    def test_create_transition_minimal(self):
        """Test creating a transition with minimal fields."""
        transition = StateTransition(to_state=FeatureStatus.DRAFT)

        assert transition.from_state is None
        assert transition.to_state == FeatureStatus.DRAFT
        assert isinstance(transition.timestamp, datetime)
        assert transition.reason is None

    def test_transition_timestamp_auto_generated(self):
        """Test that timestamp is automatically generated."""
        before = datetime.now()
        transition = StateTransition(to_state=FeatureStatus.DRAFT)
        after = datetime.now()

        assert before <= transition.timestamp <= after


class TestFeatureState:
    """Tests for FeatureState model."""

    def test_create_initial_state(self):
        """Test creating initial state for a feature."""
        state = FeatureState.create_initial("test-feature")

        assert state.feature_name == "test-feature"
        assert state.status == FeatureStatus.DRAFT
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.last_activity, datetime)
        assert len(state.transitions) == 1
        assert state.transitions[0].from_state is None
        assert state.transitions[0].to_state == FeatureStatus.DRAFT
        assert state.transitions[0].reason == "Feature created"
        assert state.merge_commit is None
        assert state.merge_error is None
        assert state.drop_reason is None

    def test_valid_transition_draft_to_in_progress(self):
        """Test valid transition from DRAFT to IN_PROGRESS."""
        state = FeatureState.create_initial("test-feature")
        original_activity = state.last_activity

        state.transition_to(FeatureStatus.IN_PROGRESS, "Starting work")

        assert state.status == FeatureStatus.IN_PROGRESS
        assert len(state.transitions) == 2
        assert state.transitions[1].from_state == FeatureStatus.DRAFT
        assert state.transitions[1].to_state == FeatureStatus.IN_PROGRESS
        assert state.transitions[1].reason == "Starting work"
        assert state.last_activity > original_activity

    def test_valid_transition_in_progress_to_ready(self):
        """Test valid transition from IN_PROGRESS to READY."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS, "Starting work")

        state.transition_to(FeatureStatus.READY, "Work complete")

        assert state.status == FeatureStatus.READY
        assert len(state.transitions) == 3

    def test_valid_transition_ready_to_completed(self):
        """Test valid transition from READY to COMPLETED."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)
        state.transition_to(FeatureStatus.READY)

        state.transition_to(FeatureStatus.COMPLETED, "Merged to main")

        assert state.status == FeatureStatus.COMPLETED
        assert len(state.transitions) == 4

    def test_valid_transition_draft_to_dropped(self):
        """Test valid transition from DRAFT to DROPPED."""
        state = FeatureState.create_initial("test-feature")

        state.transition_to(FeatureStatus.DROPPED, "No longer needed")

        assert state.status == FeatureStatus.DROPPED
        assert len(state.transitions) == 2
        assert state.transitions[1].reason == "No longer needed"

    def test_valid_transition_ready_to_in_progress(self):
        """Test valid backward transition from READY to IN_PROGRESS."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)
        state.transition_to(FeatureStatus.READY)

        # Should be able to go back to IN_PROGRESS
        state.transition_to(FeatureStatus.IN_PROGRESS, "Need more work")

        assert state.status == FeatureStatus.IN_PROGRESS

    def test_valid_transition_ready_to_merge_conflict(self):
        """Test valid transition from READY to MERGE_CONFLICT."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)
        state.transition_to(FeatureStatus.READY)

        state.transition_to(FeatureStatus.MERGE_CONFLICT, "Merge failed")

        assert state.status == FeatureStatus.MERGE_CONFLICT
        assert len(state.transitions) == 4

    def test_valid_transition_merge_conflict_to_completed(self):
        """Test valid transition from MERGE_CONFLICT to COMPLETED."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)
        state.transition_to(FeatureStatus.READY)
        state.transition_to(FeatureStatus.MERGE_CONFLICT)

        # After resolving conflicts manually
        state.transition_to(FeatureStatus.COMPLETED, "Conflicts resolved")

        assert state.status == FeatureStatus.COMPLETED

    def test_valid_transition_merge_conflict_to_ready(self):
        """Test valid transition from MERGE_CONFLICT back to READY."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)
        state.transition_to(FeatureStatus.READY)
        state.transition_to(FeatureStatus.MERGE_CONFLICT, "Merge failed")

        # User wants to retry merge
        state.transition_to(FeatureStatus.READY, "Ready to retry")

        assert state.status == FeatureStatus.READY

    def test_valid_transition_merge_conflict_to_dropped(self):
        """Test valid transition from MERGE_CONFLICT to DROPPED."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)
        state.transition_to(FeatureStatus.READY)
        state.transition_to(FeatureStatus.MERGE_CONFLICT)

        # Give up on the feature
        state.transition_to(FeatureStatus.DROPPED, "Too many conflicts")

        assert state.status == FeatureStatus.DROPPED

    def test_invalid_transition_draft_to_ready(self):
        """Test invalid transition from DRAFT to READY."""
        state = FeatureState.create_initial("test-feature")

        with pytest.raises(ValueError, match="Invalid state transition"):
            state.transition_to(FeatureStatus.READY)

    def test_invalid_transition_draft_to_completed(self):
        """Test invalid transition from DRAFT to COMPLETED."""
        state = FeatureState.create_initial("test-feature")

        with pytest.raises(ValueError, match="Invalid state transition"):
            state.transition_to(FeatureStatus.COMPLETED)

    def test_invalid_transition_in_progress_to_completed(self):
        """Test invalid transition from IN_PROGRESS to COMPLETED."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)

        with pytest.raises(ValueError, match="Invalid state transition"):
            state.transition_to(FeatureStatus.COMPLETED)

    def test_terminal_state_completed_no_transitions(self):
        """Test that COMPLETED state has no valid transitions."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)
        state.transition_to(FeatureStatus.READY)
        state.transition_to(FeatureStatus.COMPLETED)

        # Try all possible transitions - all should fail
        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.DRAFT)

        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.IN_PROGRESS)

        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.READY)

        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.DROPPED)

    def test_terminal_state_dropped_no_transitions(self):
        """Test that DROPPED state has no valid transitions."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.DROPPED)

        # Try all possible transitions - all should fail
        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.DRAFT)

        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.IN_PROGRESS)

        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.READY)

        with pytest.raises(ValueError):
            state.transition_to(FeatureStatus.COMPLETED)

    def test_save_and_load_state(self):
        """Test saving and loading state from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # Create and save state
            original_state = FeatureState.create_initial("test-feature")
            original_state.transition_to(FeatureStatus.IN_PROGRESS, "Starting work")
            original_state.merge_commit = "abc123"
            original_state.save(state_file)

            # Load state
            loaded_state = FeatureState.load(state_file)

            # Verify loaded state matches original
            assert loaded_state.feature_name == original_state.feature_name
            assert loaded_state.status == original_state.status
            assert loaded_state.merge_commit == original_state.merge_commit
            assert len(loaded_state.transitions) == len(original_state.transitions)

    def test_save_creates_parent_directories(self):
        """Test that save creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "nested" / "dirs" / "state.yaml"

            state = FeatureState.create_initial("test-feature")
            state.save(state_file)

            assert state_file.exists()
            assert state_file.parent.exists()

    def test_load_nonexistent_file_raises_error(self):
        """Test that loading nonexistent file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "nonexistent.yaml"

            with pytest.raises(FileNotFoundError):
                FeatureState.load(state_file)

    def test_save_produces_valid_yaml(self):
        """Test that saved state is valid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            state = FeatureState.create_initial("test-feature")
            state.transition_to(FeatureStatus.IN_PROGRESS)
            state.save(state_file)

            # Load as raw YAML
            with open(state_file) as f:
                data = yaml.safe_load(f)

            assert data["feature_name"] == "test-feature"
            assert data["status"] == "in-progress"
            assert "created_at" in data
            assert "last_activity" in data
            assert len(data["transitions"]) == 2

    def test_timestamps_preserved_through_save_load(self):
        """Test that timestamps are preserved through save/load cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # Create state with specific timestamp
            original_time = datetime(2025, 1, 1, 12, 0, 0)
            state = FeatureState(
                feature_name="test-feature",
                status=FeatureStatus.DRAFT,
                created_at=original_time,
                last_activity=original_time,
                transitions=[],
            )
            state.save(state_file)

            # Load and verify
            loaded_state = FeatureState.load(state_file)
            assert loaded_state.created_at == original_time
            assert loaded_state.last_activity == original_time

    def test_transition_history_preserved(self):
        """Test that complete transition history is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # Create state with multiple transitions
            state = FeatureState.create_initial("test-feature")
            state.transition_to(FeatureStatus.IN_PROGRESS, "Start work")
            state.transition_to(FeatureStatus.READY, "Work done")
            state.transition_to(FeatureStatus.IN_PROGRESS, "Need fixes")
            state.transition_to(FeatureStatus.READY, "Fixes done")
            state.save(state_file)

            # Load and verify
            loaded_state = FeatureState.load(state_file)
            assert len(loaded_state.transitions) == 5
            assert loaded_state.transitions[0].to_state == FeatureStatus.DRAFT
            assert loaded_state.transitions[1].to_state == FeatureStatus.IN_PROGRESS
            assert loaded_state.transitions[2].to_state == FeatureStatus.READY
            assert loaded_state.transitions[3].to_state == FeatureStatus.IN_PROGRESS
            assert loaded_state.transitions[4].to_state == FeatureStatus.READY

    def test_merge_commit_and_drop_reason_preserved(self):
        """Test that merge_commit and drop_reason are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # Test with merge_commit
            state = FeatureState.create_initial("completed-feature")
            state.transition_to(FeatureStatus.IN_PROGRESS)
            state.transition_to(FeatureStatus.READY)
            state.transition_to(FeatureStatus.COMPLETED)
            state.merge_commit = "abc123def456"
            state.save(state_file)

            loaded_state = FeatureState.load(state_file)
            assert loaded_state.merge_commit == "abc123def456"

            # Test with drop_reason
            state2_file = Path(tmpdir) / "state2.yaml"
            state2 = FeatureState.create_initial("dropped-feature")
            state2.transition_to(FeatureStatus.DROPPED)
            state2.drop_reason = "Obsolete requirement"
            state2.save(state2_file)

            loaded_state2 = FeatureState.load(state2_file)
            assert loaded_state2.drop_reason == "Obsolete requirement"

    def test_merge_error_preserved(self):
        """Test that merge_error is preserved through save/load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # Create state with merge conflict
            state = FeatureState.create_initial("conflict-feature")
            state.transition_to(FeatureStatus.IN_PROGRESS)
            state.transition_to(FeatureStatus.READY)
            state.transition_to(FeatureStatus.MERGE_CONFLICT)
            state.merge_error = "error: The following untracked working tree files..."
            state.save(state_file)

            loaded_state = FeatureState.load(state_file)
            assert (
                loaded_state.merge_error == "error: The following untracked working tree files..."
            )
            assert loaded_state.status == FeatureStatus.MERGE_CONFLICT


class TestStateUtils:
    """Tests for state utility functions."""

    @patch("weft.state.utils.WeftRuntime")
    def test_get_state_file(self, mock_runtime_class):
        """Test getting state file path."""
        mock_runtime = MagicMock()
        mock_runtime.base_dir = Path("/mock/.weft")
        mock_runtime_class.return_value = mock_runtime

        state_file = get_state_file("test-feature")

        assert state_file == Path("/mock/.weft/features/test-feature/state.yaml")

    @patch("weft.state.utils.WeftRuntime")
    def test_get_feature_state_existing(self, mock_runtime_class):
        """Test getting existing feature state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock runtime
            mock_runtime = MagicMock()
            mock_runtime.base_dir = Path(tmpdir)
            mock_runtime_class.return_value = mock_runtime

            # Create existing state
            state_file = Path(tmpdir) / "features" / "test-feature" / "state.yaml"
            state_file.parent.mkdir(parents=True)
            original_state = FeatureState.create_initial("test-feature")
            original_state.transition_to(FeatureStatus.IN_PROGRESS)
            original_state.save(state_file)

            # Get state
            loaded_state = get_feature_state("test-feature")

            assert loaded_state.feature_name == "test-feature"
            assert loaded_state.status == FeatureStatus.IN_PROGRESS

    @patch("weft.state.utils.WeftRuntime")
    def test_get_feature_state_creates_if_missing(self, mock_runtime_class):
        """Test that get_feature_state creates state if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock runtime
            mock_runtime = MagicMock()
            mock_runtime.base_dir = Path(tmpdir)
            mock_runtime_class.return_value = mock_runtime

            # Get state (doesn't exist yet)
            state = get_feature_state("new-feature")

            # Verify state was created
            assert state.feature_name == "new-feature"
            assert state.status == FeatureStatus.DRAFT

            # Verify state file was created
            state_file = Path(tmpdir) / "features" / "new-feature" / "state.yaml"
            assert state_file.exists()

    @patch("weft.state.utils.WeftRuntime")
    def test_list_features_by_state_all(self, mock_runtime_class):
        """Test listing all features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock runtime
            mock_runtime = MagicMock()
            mock_runtime.base_dir = Path(tmpdir)
            mock_runtime_class.return_value = mock_runtime

            features_dir = Path(tmpdir) / "features"
            features_dir.mkdir()

            # Create multiple features with different states
            for name, status in [
                ("feature-1", FeatureStatus.DRAFT),
                ("feature-2", FeatureStatus.IN_PROGRESS),
                ("feature-3", FeatureStatus.READY),
            ]:
                state_file = features_dir / name / "state.yaml"
                state_file.parent.mkdir()
                state = FeatureState.create_initial(name)
                if status == FeatureStatus.IN_PROGRESS:
                    state.transition_to(FeatureStatus.IN_PROGRESS)
                elif status == FeatureStatus.READY:
                    state.transition_to(FeatureStatus.IN_PROGRESS)
                    state.transition_to(FeatureStatus.READY)
                state.save(state_file)

            # List all features
            states = list_features_by_state()

            assert len(states) == 3
            names = {s.feature_name for s in states}
            assert names == {"feature-1", "feature-2", "feature-3"}

    @patch("weft.state.utils.WeftRuntime")
    def test_list_features_by_state_filtered(self, mock_runtime_class):
        """Test listing features filtered by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock runtime
            mock_runtime = MagicMock()
            mock_runtime.base_dir = Path(tmpdir)
            mock_runtime_class.return_value = mock_runtime

            features_dir = Path(tmpdir) / "features"
            features_dir.mkdir()

            # Create multiple features with different states
            for name, status in [
                ("draft-1", FeatureStatus.DRAFT),
                ("draft-2", FeatureStatus.DRAFT),
                ("in-progress-1", FeatureStatus.IN_PROGRESS),
                ("ready-1", FeatureStatus.READY),
            ]:
                state_file = features_dir / name / "state.yaml"
                state_file.parent.mkdir()
                state = FeatureState.create_initial(name)
                if status == FeatureStatus.IN_PROGRESS:
                    state.transition_to(FeatureStatus.IN_PROGRESS)
                elif status == FeatureStatus.READY:
                    state.transition_to(FeatureStatus.IN_PROGRESS)
                    state.transition_to(FeatureStatus.READY)
                state.save(state_file)

            # List only DRAFT features
            draft_states = list_features_by_state(FeatureStatus.DRAFT)
            assert len(draft_states) == 2
            names = {s.feature_name for s in draft_states}
            assert names == {"draft-1", "draft-2"}

            # List only IN_PROGRESS features
            in_progress_states = list_features_by_state(FeatureStatus.IN_PROGRESS)
            assert len(in_progress_states) == 1
            assert in_progress_states[0].feature_name == "in-progress-1"

    @patch("weft.state.utils.WeftRuntime")
    def test_list_features_empty_directory(self, mock_runtime_class):
        """Test listing features when directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock runtime with non-existent features dir
            mock_runtime = MagicMock()
            mock_runtime.base_dir = Path(tmpdir)
            mock_runtime_class.return_value = mock_runtime

            states = list_features_by_state()

            assert states == []

    @patch("weft.state.utils.WeftRuntime")
    def test_list_features_skips_invalid_states(self, mock_runtime_class):
        """Test that list_features_by_state skips invalid state files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock runtime
            mock_runtime = MagicMock()
            mock_runtime.base_dir = Path(tmpdir)
            mock_runtime_class.return_value = mock_runtime

            features_dir = Path(tmpdir) / "features"
            features_dir.mkdir()

            # Create valid state
            valid_dir = features_dir / "valid-feature"
            valid_dir.mkdir()
            valid_state = FeatureState.create_initial("valid-feature")
            valid_state.save(valid_dir / "state.yaml")

            # Create invalid state (bad YAML)
            invalid_dir = features_dir / "invalid-feature"
            invalid_dir.mkdir()
            with open(invalid_dir / "state.yaml", "w") as f:
                f.write("invalid: yaml: content: [[[")

            # List should only return valid feature
            states = list_features_by_state()
            assert len(states) == 1
            assert states[0].feature_name == "valid-feature"

    @patch("weft.state.utils.WeftRuntime")
    def test_list_features_skips_non_directories(self, mock_runtime_class):
        """Test that list_features_by_state skips non-directory items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock runtime
            mock_runtime = MagicMock()
            mock_runtime.base_dir = Path(tmpdir)
            mock_runtime_class.return_value = mock_runtime

            features_dir = Path(tmpdir) / "features"
            features_dir.mkdir()

            # Create valid feature
            feature_dir = features_dir / "feature-1"
            feature_dir.mkdir()
            state = FeatureState.create_initial("feature-1")
            state.save(feature_dir / "state.yaml")

            # Create a regular file (not directory)
            (features_dir / "some-file.txt").write_text("not a feature")

            # List should only return the feature directory
            states = list_features_by_state()
            assert len(states) == 1
            assert states[0].feature_name == "feature-1"


class TestFeatureLifecycle:
    """Integration tests for complete feature lifecycle."""

    def test_complete_lifecycle_draft_to_completed(self):
        """Test complete lifecycle: DRAFT → IN_PROGRESS → READY → COMPLETED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # 1. Create feature (DRAFT)
            state = FeatureState.create_initial("test-feature")
            assert state.status == FeatureStatus.DRAFT
            state.save(state_file)

            # 2. Start work (IN_PROGRESS)
            state = FeatureState.load(state_file)
            state.transition_to(FeatureStatus.IN_PROGRESS, "Spec approved")
            assert state.status == FeatureStatus.IN_PROGRESS
            state.save(state_file)

            # 3. Complete agents (READY)
            state = FeatureState.load(state_file)
            state.transition_to(FeatureStatus.READY, "All agents done")
            assert state.status == FeatureStatus.READY
            state.save(state_file)

            # 4. Merge (COMPLETED)
            state = FeatureState.load(state_file)
            state.merge_commit = "abc123"
            state.transition_to(FeatureStatus.COMPLETED, "Merged to main")
            assert state.status == FeatureStatus.COMPLETED
            state.save(state_file)

            # Verify final state
            final_state = FeatureState.load(state_file)
            assert final_state.status == FeatureStatus.COMPLETED
            assert final_state.merge_commit == "abc123"
            assert len(final_state.transitions) == 4

    def test_complete_lifecycle_draft_to_dropped(self):
        """Test lifecycle ending in drop: DRAFT → DROPPED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # 1. Create feature (DRAFT)
            state = FeatureState.create_initial("bad-feature")
            state.save(state_file)

            # 2. Drop immediately (DROPPED)
            state = FeatureState.load(state_file)
            state.drop_reason = "Obsolete requirement"
            state.transition_to(FeatureStatus.DROPPED, "No longer needed")
            state.save(state_file)

            # Verify final state
            final_state = FeatureState.load(state_file)
            assert final_state.status == FeatureStatus.DROPPED
            assert final_state.drop_reason == "Obsolete requirement"
            assert len(final_state.transitions) == 2

    def test_lifecycle_with_iteration(self):
        """Test lifecycle with iteration back to IN_PROGRESS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # Create and advance to READY
            state = FeatureState.create_initial("iterative-feature")
            state.transition_to(FeatureStatus.IN_PROGRESS)
            state.transition_to(FeatureStatus.READY)
            state.save(state_file)

            # Go back to IN_PROGRESS
            state = FeatureState.load(state_file)
            state.transition_to(FeatureStatus.IN_PROGRESS, "Found issues")
            state.save(state_file)

            # Back to READY
            state = FeatureState.load(state_file)
            state.transition_to(FeatureStatus.READY, "Issues fixed")
            state.save(state_file)

            # Complete
            state = FeatureState.load(state_file)
            state.transition_to(FeatureStatus.COMPLETED)
            state.save(state_file)

            # Verify transition history
            final_state = FeatureState.load(state_file)
            assert len(final_state.transitions) == 6
            # DRAFT → IN_PROGRESS → READY → IN_PROGRESS → READY → COMPLETED

    def test_idempotent_transition(self):
        """Test that transitioning to the same state is idempotent."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.IN_PROGRESS)

        # Record transition count after first transition
        transitions_before = len(state.transitions)

        # Should succeed without error
        state.transition_to(FeatureStatus.IN_PROGRESS)

        # Should still be in IN_PROGRESS with no new transition recorded
        assert state.status == FeatureStatus.IN_PROGRESS
        assert len(state.transitions) == transitions_before

    def test_idempotent_dropped_transition(self):
        """Test that dropping an already-dropped feature is idempotent."""
        state = FeatureState.create_initial("test-feature")
        state.transition_to(FeatureStatus.DROPPED, "First drop")

        # Record transition count after first drop
        transitions_before = len(state.transitions)

        # Try to drop again - should succeed without error
        state.transition_to(FeatureStatus.DROPPED, "Second drop")

        # Should still be DROPPED with no new transition recorded
        assert state.status == FeatureStatus.DROPPED
        assert len(state.transitions) == transitions_before

    def test_lifecycle_with_merge_conflict_then_retry(self):
        """Test lifecycle: READY → MERGE_CONFLICT → READY → COMPLETED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # 1. Create and advance to READY
            state = FeatureState.create_initial("conflict-feature")
            state.transition_to(FeatureStatus.IN_PROGRESS, "Spec approved")
            state.transition_to(FeatureStatus.READY, "All agents done")
            state.save(state_file)

            # 2. Try to merge - fails with conflict
            state = FeatureState.load(state_file)
            state.merge_error = "error: untracked files would be overwritten"
            state.transition_to(FeatureStatus.MERGE_CONFLICT, "Merge failed")
            state.save(state_file)

            # 3. User resolves conflicts manually, retry merge
            state = FeatureState.load(state_file)
            assert state.status == FeatureStatus.MERGE_CONFLICT
            assert state.merge_error is not None

            # Clear error and go back to ready
            state.merge_error = None
            state.transition_to(FeatureStatus.READY, "Conflicts resolved")
            state.save(state_file)

            # 4. Retry merge - succeeds this time
            state = FeatureState.load(state_file)
            state.merge_commit = "abc123"
            state.transition_to(FeatureStatus.COMPLETED, "Merged successfully")
            state.save(state_file)

            # Verify final state
            final_state = FeatureState.load(state_file)
            assert final_state.status == FeatureStatus.COMPLETED
            assert final_state.merge_commit == "abc123"
            assert final_state.merge_error is None
            # DRAFT → IN_PROGRESS → READY → MERGE_CONFLICT → READY → COMPLETED
            assert len(final_state.transitions) == 6

    def test_lifecycle_with_merge_conflict_then_drop(self):
        """Test lifecycle: READY → MERGE_CONFLICT → DROPPED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.yaml"

            # 1. Create and advance to READY
            state = FeatureState.create_initial("bad-conflict-feature")
            state.transition_to(FeatureStatus.IN_PROGRESS)
            state.transition_to(FeatureStatus.READY)
            state.save(state_file)

            # 2. Try to merge - fails with conflict
            state = FeatureState.load(state_file)
            state.merge_error = "error: too many conflicts"
            state.transition_to(FeatureStatus.MERGE_CONFLICT, "Merge failed")
            state.save(state_file)

            # 3. User decides conflicts are too hard, drops feature
            state = FeatureState.load(state_file)
            state.drop_reason = "Conflicts too complex to resolve"
            state.transition_to(FeatureStatus.DROPPED, "Giving up")
            state.save(state_file)

            # Verify final state
            final_state = FeatureState.load(state_file)
            assert final_state.status == FeatureStatus.DROPPED
            assert final_state.drop_reason == "Conflicts too complex to resolve"
            assert final_state.merge_error == "error: too many conflicts"
            # DRAFT → IN_PROGRESS → READY → MERGE_CONFLICT → DROPPED
            assert len(final_state.transitions) == 5
