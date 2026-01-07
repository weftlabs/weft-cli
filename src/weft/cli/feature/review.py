"""Review feature and decide to accept, drop, or continue."""

import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import click

from weft.cli.utils import echo_section_start, safe_get_settings
from weft.git.exceptions import GitError
from weft.git.worktree import get_worktree_path, get_worktree_status, remove_worktree
from weft.state import FeatureStatus, get_feature_state, get_state_file, load_feature_state
from weft.state.exceptions import StateError


def get_agent_outputs(feature_name: str, ai_history_path: Path) -> dict[str, str | None]:
    """Get outputs from all agents for a feature."""
    agents = ["00-meta", "01-architect", "02-openapi", "03-ui", "04-integration", "05-test"]
    outputs: dict[str, str | None] = {}

    for agent in agents:
        output_dir = ai_history_path / feature_name / agent / "out"
        if not output_dir.exists():
            outputs[agent] = None
            continue

        results = list(output_dir.glob("*_result.md"))
        if not results:
            outputs[agent] = None
            continue

        latest = max(results, key=lambda p: p.stat().st_mtime)
        outputs[agent] = latest.read_text()

    return outputs


def extract_code_blocks(text: str) -> list[tuple[str | None, str]]:
    """Extract code blocks from markdown text."""
    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return [(lang or None, code.strip()) for lang, code in matches]


def display_summary(outputs: dict[str, str | None]) -> None:
    """Display summary of all agent outputs."""
    echo_section_start("FEATURE REVIEW - AGENT SUMMARY")

    agent_names = {
        "00-meta": "Meta (Feature Understanding)",
        "01-architect": "Architect (Domain Modeling)",
        "02-openapi": "OpenAPI (Specification)",
        "03-ui": "UI (Frontend Skeleton)",
        "04-integration": "Integration (API Wiring)",
        "05-test": "Test (Test Generation)",
    }

    for agent, name in agent_names.items():
        output = outputs.get(agent)
        if output is None:
            click.echo(f"❌ {name}: No output generated")
            continue

        lines = output.split("\n")
        start_idx = 0
        if lines[0].startswith("---"):
            try:
                end_idx = lines[1:].index("---") + 1
                start_idx = end_idx + 1
            except ValueError:
                pass

        summary_lines = []
        for line in lines[start_idx:]:
            line = line.strip()
            if line and not line.startswith("#"):
                summary_lines.append(line)
                if len(summary_lines) >= 3:
                    break

        summary = " ".join(summary_lines)[:150]
        if len(summary) == 150:
            summary += "..."

        click.echo(f"✓ {name}")
        click.echo(f"  {summary}\n")


def show_ai_generated_files(feature_name: str, worktree_path: Path) -> None:
    """Show summary of AI-generated files in the worktree."""
    echo_section_start("AI-GENERATED FILES")

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )

        files = [f.strip() for f in result.stdout.split("\n") if f.strip()]

        if not files:
            click.echo("  (No files added or modified)\n")
            return

        by_dir = defaultdict(list)

        for f in files:
            parts = Path(f).parts
            if len(parts) > 1:
                dir_name = "/".join(parts[:-1])
                by_dir[dir_name].append(parts[-1])
            else:
                by_dir["<root>"].append(f)

        for dir_name in sorted(by_dir.keys()):
            click.echo(f"  {dir_name}/")
            for file_name in sorted(by_dir[dir_name]):
                click.echo(f"    • {file_name}")

        click.echo(f"\n  Total: {len(files)} file(s)\n")

    except subprocess.CalledProcessError as e:
        click.echo(f"  ⚠  Could not list files: {e}\n", err=True)


def show_test_results(feature_name: str, ai_history_path: Path) -> bool:
    """Show test results from test agent output. Returns True if tests passed."""
    echo_section_start("TEST RESULTS")

    test_agent_dir = ai_history_path / feature_name / "05-test" / "out"

    if not test_agent_dir.exists():
        click.echo("  (No test agent output found)\n")
        return True

    result_files = sorted(
        test_agent_dir.glob("*_result.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not result_files:
        click.echo("  (No test results found)\n")
        return True

    result_file = result_files[0]
    content = result_file.read_text(encoding="utf-8")

    if "test_results" in content:
        try:
            passed_match = re.search(r"Tests passed:\s*(\d+)/(\d+)", content)
            if passed_match:
                passed = int(passed_match.group(1))
                total = int(passed_match.group(2))
                click.echo(f"  ✓ {passed}/{total} tests passed")
                click.echo("  Runner: pytest/jest\n")
                return passed == total

            if "tests_passed: true" in content.lower():
                click.echo("  ✓ All tests passed\n")
                return True
            elif "tests_passed: false" in content.lower():
                click.echo("  ✗ Some tests failed")
                click.echo(f"  See details: {result_file}\n")
                return False

        except Exception as e:
            click.echo(f"  ⚠  Could not parse test results: {e}\n", err=True)
            return True

    if any(keyword in content for keyword in ["pytest", "jest", "test suite"]):
        click.echo("  ✓ Tests generated and executed")
        click.echo(f"  See details: {result_file}\n")
        return True
    else:
        click.echo("  ℹ  Test specifications generated (not executed)\n")
        return True


def handle_accept(
    feature_name: str,
    code_repo_path: Path,
    ai_history_path: Path,
    worktree_path: Path,
    base_branch: str,
) -> None:
    """Handle feature acceptance (merge to main)."""
    echo_section_start("ACCEPTING FEATURE")

    # Check git status
    try:
        status = get_worktree_status(worktree_path)
    except GitError as e:
        click.echo(f"❌ Error checking worktree status: {e}", err=True)
        raise click.Abort() from e

    # Handle dirty worktree
    if not status.is_clean:
        click.echo("⚠  Worktree has uncommitted changes:")
        for f in status.modified_files:
            click.echo(f"  M {f}")
        for f in status.untracked_files:
            click.echo(f"  ? {f}")
        click.echo()

        if not click.confirm("Commit these changes before merging?", default=True):
            click.echo("❌ Feature acceptance cancelled")
            raise click.Abort()

        commit_msg = click.prompt("Commit message", default=f"Complete {feature_name}")

        try:
            subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=worktree_path,
                check=True,
                capture_output=True,
            )
            click.echo(f"✓ Changes committed: {commit_msg}\n")
        except subprocess.CalledProcessError as e:
            click.echo(f"❌ Error committing changes: {e.stderr}", err=True)
            raise click.Abort() from e

    # Merge to base branch
    click.echo(f"🔀 Merging to {base_branch}...")

    try:
        subprocess.run(
            ["git", "checkout", base_branch],
            cwd=code_repo_path,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            [
                "git",
                "merge",
                "--no-ff",
                f"feature/{feature_name}",
                "-m",
                f"Merge feature: {feature_name}",
            ],
            cwd=code_repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        merge_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=code_repo_path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        click.echo(f"✓ Merged to {base_branch}")
        click.echo(f"  Merge commit: {merge_commit[:8]}\n")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or str(e)
        click.echo(f"❌ Error merging: {error_msg}", err=True)

        # Update feature state to merge-conflict instead of aborting
        try:
            state = load_feature_state(feature_name)
            state.merge_error = error_msg
            state.transition_to(FeatureStatus.MERGE_CONFLICT, reason="Merge failed")
            state_file = get_state_file(feature_name)
            state.save(state_file)
            click.echo("\n⚠️  Feature state updated to 'merge-conflict'")
        except Exception as state_err:
            click.echo(f"⚠  Could not update state: {state_err}", err=True)

        click.echo("\n💡 To resolve conflicts:")
        click.echo(f"  1. cd {code_repo_path}")
        click.echo("  2. Resolve conflicts in the files")
        click.echo("  3. git add <resolved-files>")
        click.echo("  4. git merge --continue")
        click.echo("\n💡 Then retry the merge:")
        click.echo(f"  weft feature review {feature_name}")
        click.echo("  (Choose 'accept' again to retry merge)")
        click.echo(f"\n📁 Worktree preserved at: {worktree_path}")
        click.echo(f"   Review generated code: weft feature review {feature_name}")
        click.echo(f"   Give up and drop: weft feature drop {feature_name}")
        raise click.Abort() from e

    # Update AI history
    completion_file = ai_history_path / feature_name / "COMPLETED.md"
    completion_content = (
        f"# Feature Completed\n\n"
        f"Feature: {feature_name}\n"
        f"Merge Commit: {merge_commit}\n"
        f"Completed: {datetime.now().isoformat()}\n"
    )
    completion_file.write_text(completion_content)

    try:
        subprocess.run(
            ["git", "add", str(completion_file)],
            cwd=ai_history_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"Mark {feature_name} as completed (merge: {merge_commit[:8]})",
            ],
            cwd=ai_history_path,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        pass

    # Update feature state
    try:
        state = load_feature_state(feature_name)
        state.transition_to(FeatureStatus.COMPLETED, reason="Feature accepted and merged")
        state_file = get_state_file(feature_name)
        state.save(state_file)
    except StateError:
        pass

    # Remove worktree
    click.echo("🧹 Cleaning up worktree...")
    success = remove_worktree(code_repo_path, feature_name, delete_branch=True)

    if success:
        click.echo("✓ Worktree and branch removed\n")
    else:
        click.echo("⚠  Could not remove worktree automatically")
        click.echo(f"  Remove manually: git worktree remove {worktree_path}\n")

    echo_section_start("✅ FEATURE ACCEPTED AND MERGED")


def handle_drop(
    feature_name: str,
    code_repo_path: Path,
    ai_history_path: Path,
    worktree_path: Path,
    delete_history: bool,
    reason: str | None,
) -> None:
    """Handle feature drop (abandon without merging)."""
    echo_section_start("DROPPING FEATURE")

    # Check if already dropped
    feature_history = ai_history_path / feature_name
    dropped_marker = feature_history / "DROPPED.md"

    if dropped_marker.exists():
        click.echo(f"ℹ️  Feature '{feature_name}' is already dropped\n")

        if not delete_history:
            echo_section_start("✅ FEATURE ALREADY DROPPED")
            click.echo("💡 Use --delete-history to permanently remove AI history")
            return

        # If delete_history is requested, confirm and proceed to delete
        if not click.confirm("Permanently delete AI history?", default=False):
            click.echo("❌ Delete cancelled")
            raise click.Abort()

        click.echo("🗑️  Deleting AI history...")
        import shutil

        shutil.rmtree(feature_history)
        click.echo("✓ AI history deleted\n")
        echo_section_start("✅ AI HISTORY DELETED")
        return

    # Confirm
    if not click.confirm(f"⚠️  Permanently drop feature '{feature_name}'?", default=False):
        click.echo("❌ Feature drop cancelled")
        raise click.Abort()

    # Remove worktree
    if worktree_path.exists():
        click.echo("🧹 Removing worktree and branch...")
        success = remove_worktree(code_repo_path, feature_name, delete_branch=True)
        if success:
            click.echo("✓ Worktree and branch removed\n")
        else:
            click.echo("⚠  Could not remove worktree automatically\n")

    # Handle AI history
    if delete_history and feature_history.exists():
        click.echo("🗑️  Deleting AI history...")
        import shutil

        shutil.rmtree(feature_history)
        click.echo("✓ AI history deleted\n")
    elif feature_history.exists():
        # Mark as dropped
        dropped_content = (
            f"# Feature Dropped\n\n"
            f"Feature: {feature_name}\n"
            f"Dropped: {datetime.now().isoformat()}\n"
        )
        if reason:
            dropped_content += f"Reason: {reason}\n"

        dropped_marker.write_text(dropped_content)

        try:
            subprocess.run(
                ["git", "add", str(dropped_marker)],
                cwd=ai_history_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Mark {feature_name} as dropped"],
                cwd=ai_history_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            pass

        click.echo("✓ AI history marked as dropped (preserved for audit)\n")

    # Update feature state
    try:
        state = load_feature_state(feature_name)
        state.transition_to(FeatureStatus.DROPPED, reason=reason or "Feature dropped by user")
        state_file = get_state_file(feature_name)
        state.save(state_file)
    except StateError:
        pass

    echo_section_start("✅ FEATURE DROPPED")


@click.command()
@click.argument("feature_name")
@click.option(
    "--base-branch",
    default="main",
    help="Base branch to merge into if accepting (default: main)",
)
@click.option(
    "--delete-history",
    is_flag=True,
    help="Delete AI history if dropping (default: preserve)",
)
@click.option(
    "--reason",
    "-r",
    help="Reason for dropping (for audit trail)",
)
def review(
    feature_name: str,
    base_branch: str,
    delete_history: bool,
    reason: str | None,
) -> None:
    """Review feature implementation and decide next action.

    Shows comprehensive review including:
    - Agent outputs summary
    - AI-generated files
    - Test results

    Then prompts for action:
    - accept: Merge to main branch
    - drop: Abandon feature
    - continue: Exit and continue working

    Examples:
        weft feature review user-auth
        weft feature review api-v2 --base-branch develop
        weft feature review experiment --reason "Approach didn't work"
    """
    click.echo(f"\n🔍 Reviewing feature: {feature_name}\n")

    # Load settings
    settings = safe_get_settings()
    code_repo_path = settings.code_repo_path
    ai_history_path = settings.ai_history_path

    # Check feature state
    try:
        state = get_feature_state(feature_name)
        click.echo(f"Current state: {state.status.value}\n")

        if state.status in [FeatureStatus.COMPLETED, FeatureStatus.DROPPED]:
            click.echo(
                f"❌ Error: Feature is in terminal state '{state.status.value}'",
                err=True,
            )
            raise click.Abort()

        # Show merge conflict info if in that state
        if state.status == FeatureStatus.MERGE_CONFLICT:
            click.echo("⚠️  Previous merge attempt failed")
            if state.merge_error:
                click.echo(f"   Error: {state.merge_error}")
            click.echo("   You can review the code and retry merge\n")
    except FileNotFoundError:
        click.echo("⚠  No state file found for feature\n", err=True)

    # Get worktree path
    worktree_path = get_worktree_path(code_repo_path, feature_name)

    if not worktree_path.exists():
        click.echo(f"❌ Error: Worktree not found at {worktree_path}", err=True)
        click.echo("\n💡 Available features: weft feature list")
        raise click.Abort()

    # Display review
    outputs = get_agent_outputs(feature_name, ai_history_path)
    display_summary(outputs)
    show_ai_generated_files(feature_name, worktree_path)
    tests_passed = show_test_results(feature_name, ai_history_path)

    # Decision prompt
    echo_section_start("REVIEW COMPLETE")

    if not tests_passed:
        click.echo("⚠  Warning: Some tests failed\n")

    click.echo("What would you like to do?\n")
    click.echo("  accept   - Merge feature to main branch")
    click.echo("  drop     - Abandon feature without merging")
    click.echo("  continue - Exit and continue working\n")

    choice = click.prompt(
        "Decision", type=click.Choice(["accept", "drop", "continue"]), show_choices=False
    )

    if choice == "accept":
        handle_accept(feature_name, code_repo_path, ai_history_path, worktree_path, base_branch)
    elif choice == "drop":
        handle_drop(
            feature_name, code_repo_path, ai_history_path, worktree_path, delete_history, reason
        )
    else:
        click.echo("\n💡 Continue working on the feature in the worktree:")
        click.echo(f"  {worktree_path}\n")
