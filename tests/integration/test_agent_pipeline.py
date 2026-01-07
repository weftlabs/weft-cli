"""Integration tests for agent processing pipelines.

These tests verify that agents can process prompts end-to-end
with mocked AI backends using the new config-driven architecture.
"""

import subprocess
from unittest.mock import Mock

import pytest

from weft.agents import BaseSpecAgent
from weft.history.repo_manager import create_feature_structure
from weft.queue.models import PromptTask


@pytest.fixture
def test_ai_history_repo(tmp_path):
    """Create a test AI history repository."""
    history_path = tmp_path / "ai_history"
    history_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=history_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=history_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=history_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (history_path / "README.md").write_text("# AI History")
    subprocess.run(["git", "add", "README.md"], cwd=history_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=history_path,
        check=True,
        capture_output=True,
    )

    return history_path


@pytest.fixture
def mock_backend():
    """Create a mock AI backend for testing."""
    from weft.ai.backend import AIBackend

    backend = Mock(spec=AIBackend)
    backend.generate.return_value = "Mock AI response"
    backend.get_model_info.return_value = {
        "backend": "mock",
        "model": "mock-model",
        "provider": "test",
    }
    return backend


@pytest.fixture
def mock_meta_config():
    """Mock configuration for meta agent."""
    return {
        "agent_id": "00-meta",
        "agent_name": "meta",
        "spec_filename": "00_meta.md",
        "stage": "specification",
        "order_in_stage": 0,
        "description": "Feature understanding and prompt generation",
        "validation": {"required_sections": []},
    }


@pytest.fixture
def mock_architect_config():
    """Mock configuration for architect agent."""
    return {
        "agent_id": "01-architect",
        "agent_name": "architect",
        "spec_filename": "01_architect.md",
        "stage": "architecture",
        "order_in_stage": 0,
        "description": "Domain modeling and technical architecture",
        "validation": {
            "required_sections": [
                "## Domain Model",
                "## Use Cases",
                "## API Requirements",
                "## Data Flow",
                "## Trade-offs",
            ]
        },
    }


@pytest.fixture
def meta_prompt_spec(tmp_path):
    """Create a Meta agent prompt spec."""
    spec_dir = tmp_path / "specs" / "v1.0.0"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_file = spec_dir / "00_meta.md"
    spec_file.write_text(
        """# Agent 00: Meta

**Version:** 1.0.0

## Role
Feature understanding and prompt generation.

## Responsibilities
- Understand user feature requests
- Generate design briefs
- Create prompts for downstream agents

## Output Format
- Markdown with clear sections
- Next agent prompts
"""
    )
    return spec_file


@pytest.fixture
def architect_prompt_spec(tmp_path):
    """Create an Architect agent prompt spec."""
    spec_dir = tmp_path / "specs" / "v1.0.0"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_file = spec_dir / "01_architect.md"
    spec_file.write_text(
        """# Agent 01: Architect

**Version:** 1.0.0

## Role
Domain modeling and architecture design.

## Responsibilities
- Design system architecture
- Create domain models
- Identify API requirements

## Output Format
- Architecture diagrams (Mermaid)
- Domain models
- API specifications
"""
    )
    return spec_file


class TestMetaAgentPipeline:
    """Tests for Meta agent processing pipeline."""

    def test_meta_agent_initialization(
        self, test_ai_history_repo, mock_backend, meta_prompt_spec, mock_meta_config
    ):
        """Test Meta agent can be initialized."""
        feature_id = "feat-meta-init"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta"])

        # Create agent
        agent = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        assert agent.feature_id == feature_id
        assert agent.agent_id == "00-meta"
        assert agent.agent_name == "meta"
        assert agent.backend == mock_backend

    def test_meta_agent_processes_prompt(
        self, test_ai_history_repo, mock_backend, meta_prompt_spec, mock_meta_config
    ):
        """Test Meta agent processes prompt and generates output."""
        feature_id = "feat-meta-process"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta"])

        # Configure mock backend
        mock_backend.generate.return_value = """# Design Brief

## Feature: User Authentication

### Requirements
- JWT-based authentication
- Role-based access control
- Session management

### Next Steps
Agent 01 (Architect) should design the authentication architecture.
"""

        # Create watcher
        watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        # Create prompt task
        prompt_task = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="Add user authentication with JWT tokens",
            spec_version="1.0.0",
            revision=1,
        )

        # Process prompt
        output = watcher.process_prompt(prompt_task)

        # Verify output
        assert "Design Brief" in output
        assert "authentication" in output.lower()
        assert "Agent 01" in output or "Architect" in output

        # Verify backend was called
        mock_backend.generate.assert_called_once()

    def test_meta_agent_handles_complex_prompt(
        self, test_ai_history_repo, mock_backend, meta_prompt_spec, mock_meta_config
    ):
        """Test Meta agent handles complex multi-part prompts."""
        feature_id = "feat-meta-complex"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta"])

        # Configure mock backend
        mock_backend.generate.return_value = """# Design Brief

## Feature: Payment Processing System

### Components
1. Payment gateway integration
2. Transaction logging
3. Refund handling
4. Subscription management

### Architecture Considerations
- PCI DSS compliance required
- Idempotent operations
- Webhook handling

### Next Agent Prompts

**For Agent 01 (Architect):**
Design the payment processing architecture with focus on:
- Integration with Stripe API
- Transaction state machine
- Error handling and retries
"""

        watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        prompt_task = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="""Add payment processing with the following:
- Stripe integration
- Support for subscriptions and one-time payments
- Refund capabilities
- Transaction history
- Must be PCI compliant
""",
            spec_version="1.0.0",
            revision=1,
        )

        output = watcher.process_prompt(prompt_task)

        # Verify comprehensive output
        assert "Payment" in output
        assert len(output) > 100  # Should be detailed
        mock_backend.generate.assert_called_once()


class TestArchitectAgentPipeline:
    """Tests for Architect agent processing pipeline."""

    def test_architect_agent_initialization(
        self, test_ai_history_repo, mock_backend, architect_prompt_spec, mock_architect_config
    ):
        """Test Architect agent can be initialized."""
        feature_id = "feat-arch-init"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["01-architect"])

        # Create watcher
        watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="01-architect",
            config=mock_architect_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=architect_prompt_spec,
        )

        assert watcher.feature_id == feature_id
        assert watcher.agent_id == "01-architect"
        assert watcher.backend == mock_backend

    def test_architect_agent_processes_prompt(
        self, test_ai_history_repo, mock_backend, architect_prompt_spec, mock_architect_config
    ):
        """Test Architect agent processes prompt and generates architecture."""
        feature_id = "feat-arch-process"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["01-architect"])

        # Configure mock backend
        mock_backend.generate.return_value = """# Authentication Architecture

## Domain Model

```mermaid
classDiagram
    User --> Session
    User --> Role
    Session --> Token
```

## Components
1. AuthService - JWT generation/validation
2. SessionManager - Session lifecycle
3. RoleChecker - RBAC enforcement

## Use Cases
- UC1: User login with credentials
- UC2: Token refresh
- UC3: User logout
- UC4: Permission check

## Data Flow
1. User submits credentials
2. AuthService validates and generates JWT
3. SessionManager creates session
4. Token returned to client

## Trade-offs
- JWT vs session cookies: Using JWT for stateless auth
- Token expiry: 1 hour for security vs UX balance

## API Requirements
- POST /auth/login
- POST /auth/logout
- GET /auth/verify
- POST /auth/refresh
"""

        watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="01-architect",
            config=mock_architect_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=architect_prompt_spec,
        )

        prompt_task = PromptTask(
            feature_id=feature_id,
            agent_id="01-architect",
            prompt_text="Design authentication architecture with JWT and RBAC",
            spec_version="1.0.0",
            revision=1,
        )

        output = watcher.process_prompt(prompt_task)

        # Verify architectural output
        assert "Architecture" in output or "architecture" in output
        assert len(output) > 50
        mock_backend.generate.assert_called_once()


class TestMultiAgentPipeline:
    """Tests for multi-agent workflows."""

    def test_meta_to_architect_workflow(
        self,
        test_ai_history_repo,
        mock_backend,
        meta_prompt_spec,
        architect_prompt_spec,
        mock_meta_config,
        mock_architect_config,
    ):
        """Test workflow from Meta agent to Architect agent."""
        feature_id = "feat-multi-workflow"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta", "01-architect"])

        # Step 1: Meta agent processes user request
        meta_watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        mock_backend.generate.return_value = """# Design Brief

Agent 01 should design the authentication system.
"""

        meta_task = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="Add user authentication",
            spec_version="1.0.0",
            revision=1,
        )

        meta_output = meta_watcher.process_prompt(meta_task)
        assert "Design Brief" in meta_output

        # Step 2: Architect agent receives prompt
        # (In real scenario, meta output would be parsed and submitted to architect)
        arch_watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="01-architect",
            config=mock_architect_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=architect_prompt_spec,
        )

        mock_backend.generate.return_value = """# Architecture Design

## Domain Model
User, Session, Token entities

## Use Cases
- Login
- Logout

## API Requirements
- POST /auth/login

## Data Flow
Request -> Validate -> Response

## Trade-offs
JWT vs sessions
"""

        arch_task = PromptTask(
            feature_id=feature_id,
            agent_id="01-architect",
            prompt_text="Design authentication system",
            spec_version="1.0.0",
            revision=1,
        )

        arch_output = arch_watcher.process_prompt(arch_task)
        assert "Architecture" in arch_output or "Domain Model" in arch_output

        # Verify both agents processed successfully
        assert mock_backend.generate.call_count == 2

    def test_parallel_agent_processing(
        self,
        test_ai_history_repo,
        mock_backend,
        meta_prompt_spec,
        architect_prompt_spec,
        mock_meta_config,
        mock_architect_config,
    ):
        """Test multiple agents can process prompts in parallel."""
        feature_id = "feat-parallel"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta", "01-architect"])

        # Create both watchers
        meta_watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        arch_watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="01-architect",
            config=mock_architect_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=architect_prompt_spec,
        )

        # Submit tasks to both agents
        meta_task = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="Feature request A",
            spec_version="1.0.0",
            revision=1,
        )

        arch_task = PromptTask(
            feature_id=feature_id,
            agent_id="01-architect",
            prompt_text="Architecture request B",
            spec_version="1.0.0",
            revision=1,
        )

        # Process in parallel (simulate)
        # Meta agent response
        mock_backend.generate.return_value = "Meta agent response"
        meta_output = meta_watcher.process_prompt(meta_task)

        # Architect agent response (needs proper sections)
        mock_backend.generate.return_value = """# Architecture

## Domain Model
Entities

## Use Cases
UC1

## API Requirements
POST /api

## Data Flow
Flow

## Trade-offs
Tradeoff
"""
        arch_output = arch_watcher.process_prompt(arch_task)

        # Both should complete
        assert meta_output == "Meta agent response"
        assert "Architecture" in arch_output
        assert mock_backend.generate.call_count == 2


class TestAgentErrorHandling:
    """Tests for error handling in agent pipelines."""

    def test_agent_handles_backend_failure(
        self, test_ai_history_repo, mock_backend, meta_prompt_spec, mock_meta_config
    ):
        """Test agent handles AI backend failures gracefully."""
        feature_id = "feat-error-handling"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta"])

        # Configure mock to raise exception
        mock_backend.generate.side_effect = Exception("API rate limit exceeded")

        watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        prompt_task = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="Test prompt",
            spec_version="1.0.0",
            revision=1,
        )

        # Should raise exception (agents don't silently fail)
        with pytest.raises(Exception, match="API rate limit exceeded"):
            watcher.process_prompt(prompt_task)

    def test_agent_processes_multiple_prompts(
        self, test_ai_history_repo, mock_backend, meta_prompt_spec, mock_meta_config
    ):
        """Test agent can process multiple prompts sequentially."""
        feature_id = "feat-multiple-prompts"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta"])

        watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        # Process multiple prompts
        mock_backend.generate.return_value = "Response 1"
        prompt1 = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="First request",
            spec_version="1.0.0",
            revision=1,
        )
        output1 = watcher.process_prompt(prompt1)

        mock_backend.generate.return_value = "Response 2"
        prompt2 = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="Second request",
            spec_version="1.0.0",
            revision=2,
        )
        output2 = watcher.process_prompt(prompt2)

        # Both should succeed
        assert output1 == "Response 1"
        assert output2 == "Response 2"
        assert mock_backend.generate.call_count == 2

    def test_agent_with_different_spec_versions(
        self, test_ai_history_repo, mock_backend, meta_prompt_spec, mock_meta_config
    ):
        """Test agent can handle different spec versions."""
        feature_id = "feat-spec-versions"

        # Create feature structure
        create_feature_structure(test_ai_history_repo, feature_id, ["00-meta"])

        watcher = BaseSpecAgent(
            feature_id=feature_id,
            agent_id="00-meta",
            config=mock_meta_config,
            ai_history_path=test_ai_history_repo,
            backend=mock_backend,
            prompt_spec_path=meta_prompt_spec,
        )

        mock_backend.generate.return_value = "Response"

        # Spec version is just metadata - agent should process regardless
        for version in ["1.0.0", "1.1.0", "2.0.0"]:
            prompt = PromptTask(
                feature_id=feature_id,
                agent_id="00-meta",
                prompt_text="Test prompt",
                spec_version=version,
                revision=1,
            )
            output = watcher.process_prompt(prompt)
            assert output == "Response"
