#!/usr/bin/env python3
"""Weft validation script for pre-deployment and CI/CD checks."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Status(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class Check:
    name: str
    status: Status
    message: str


@dataclass
class SectionResult:
    name: str
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status in [Status.PASS, Status.SKIP, Status.WARN] for c in self.checks)


def redact_secrets(text: str) -> str:
    patterns = [
        (r"(sk-ant-[a-zA-Z0-9-]+)", "REDACTED"),
        (r"(WEFT_[A-Z_]*KEY[A-Z_]*=)([^\s]+)", r"\1REDACTED"),
        (r"(export\s+WEFT_[A-Z_]*=)([^\s]+)", r"\1REDACTED"),
        (r'(api_key\s*=\s*["\'])([^"\']+)(["\'])', r"\1REDACTED\3"),
        (r"(Bearer\s+)([^\s]+)", r"\1REDACTED"),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    return text


def tail_output(text: str, lines: int = 10) -> str:
    if not text:
        return ""

    text_lines = text.split("\n")
    if len(text_lines) <= lines:
        return text

    return "\n".join(text_lines[-lines:])


class WeftValidator:
    def __init__(self, args):
        self.args = args

    def validate_environment(self) -> SectionResult:
        result = SectionResult(name="A) Environment")

        # Check Python version
        py_version = sys.version_info
        if py_version >= (3, 8):
            result.checks.append(
                Check(
                    "Python Version",
                    Status.PASS,
                    f"Python {py_version.major}.{py_version.minor}.{py_version.micro}",
                )
            )
        else:
            result.checks.append(
                Check(
                    "Python Version",
                    Status.FAIL,
                    f"Python {py_version.major}.{py_version.minor} (requires 3.8+)",
                )
            )

        # Check Weft CLI
        weft_path = shutil.which("weft")
        if weft_path:
            result.checks.append(Check("Weft CLI", Status.PASS, f"Found at {weft_path}"))
        else:
            result.checks.append(Check("Weft CLI", Status.WARN, "Not found in PATH"))

        # Check environment variables
        required_env_vars = ["WEFT_ANTHROPIC_API_KEY"]
        for env_var in required_env_vars:
            if env_var in os.environ:
                result.checks.append(Check(f"ENV: {env_var}", Status.PASS, "Set"))
            else:
                result.checks.append(Check(f"ENV: {env_var}", Status.FAIL, "Not set"))

        return result

    def validate_repository(self) -> SectionResult:
        result = SectionResult(name="B) Repository")

        # Check if git repo
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"], check=True, capture_output=True, timeout=10
            )
            result.checks.append(Check("Git Repository", Status.PASS, "Valid git repository"))
        except (subprocess.CalledProcessError, FileNotFoundError):
            result.checks.append(Check("Git Repository", Status.FAIL, "Not a git repository"))
            return result

        # Check working tree status
        try:
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if status_result.stdout.strip():
                if self.args.allow_dirty:
                    result.checks.append(
                        Check("Working Tree", Status.WARN, "Uncommitted changes (allowed)")
                    )
                else:
                    result.checks.append(Check("Working Tree", Status.FAIL, "Uncommitted changes"))
            else:
                result.checks.append(Check("Working Tree", Status.PASS, "Clean"))
        except subprocess.CalledProcessError:
            result.checks.append(Check("Working Tree", Status.FAIL, "Could not check status"))

        return result

    def validate_commands(self) -> SectionResult:
        result = SectionResult(name="C) Commands")

        # Check pytest
        pytest_path = shutil.which("pytest")
        if pytest_path:
            result.checks.append(Check("pytest", Status.PASS, f"Found at {pytest_path}"))
        else:
            result.checks.append(Check("pytest", Status.WARN, "Not found in PATH"))

        # Check weft up (slow command, skip in quick mode)
        if self.args.quick:
            result.checks.append(
                Check("weft up", Status.SKIP, "Skipped in quick mode (slow command)")
            )
        else:
            # Would normally run weft up here
            result.checks.append(Check("weft up", Status.SKIP, "Not implemented"))

        return result

    def validate_contracts(self) -> SectionResult:
        result = SectionResult(name="D) Contracts")

        # Check .weftrc.yaml
        weftrc_path = Path(".weftrc.yaml")
        if weftrc_path.exists():
            try:
                import yaml

                with open(weftrc_path) as f:
                    yaml.safe_load(f)
                result.checks.append(Check(".weftrc.yaml", Status.PASS, "Valid YAML"))
            except ImportError:
                result.checks.append(
                    Check(
                        ".weftrc.yaml",
                        Status.WARN,
                        "Found but cannot validate (PyYAML not installed)",
                    )
                )
            except Exception as e:
                result.checks.append(Check(".weftrc.yaml", Status.FAIL, f"Invalid YAML: {e}"))
        else:
            result.checks.append(Check(".weftrc.yaml", Status.WARN, "Not found"))

        return result

    def validate_tests(self) -> SectionResult:
        result = SectionResult(name="E) Tests")

        # Skip tests if --no-tests or --quick
        if self.args.no_tests or self.args.quick:
            reason = (
                "Skipped with --no-tests flag" if self.args.no_tests else "Skipped in quick mode"
            )
            result.checks.append(Check("Test Execution", Status.SKIP, reason))
        else:
            # Would normally run pytest here
            result.checks.append(Check("Test Execution", Status.SKIP, "Not implemented"))

        return result

    def run(self) -> dict:
        sections = []

        # Map section letters to validators
        validators = {
            "A": ("validate_environment", "A) Environment"),
            "B": ("validate_repository", "B) Repository"),
            "C": ("validate_commands", "C) Commands"),
            "D": ("validate_contracts", "D) Contracts"),
            "E": ("validate_tests", "E) Tests"),
        }

        # If specific section requested, run only that one
        if self.args.section:
            section_letter = self.args.section.upper()
            if section_letter not in validators:
                print(f"Error: Invalid section '{self.args.section}'", file=sys.stderr)
                print(f"Valid sections: {', '.join(validators.keys())}", file=sys.stderr)
                sys.exit(2)

            method_name, _ = validators[section_letter]
            method = getattr(self, method_name)
            sections.append(method())
        else:
            # Run all sections
            for method_name, _ in validators.values():
                method = getattr(self, method_name)
                sections.append(method())

        # Calculate summary
        total_checks = sum(len(s.checks) for s in sections)
        passed_checks = sum(len([c for c in s.checks if c.status == Status.PASS]) for s in sections)
        failed_checks = sum(len([c for c in s.checks if c.status == Status.FAIL]) for s in sections)
        warned_checks = sum(len([c for c in s.checks if c.status == Status.WARN]) for s in sections)
        skipped_checks = sum(
            len([c for c in s.checks if c.status == Status.SKIP]) for s in sections
        )

        summary = {
            "total": total_checks,
            "passed": passed_checks,
            "failed": failed_checks,
            "warned": warned_checks,
            "skipped": skipped_checks,
        }

        return {
            "sections": [
                {
                    "name": s.name,
                    "passed": s.passed,
                    "checks": [
                        {
                            "name": c.name,
                            "status": c.status.value,
                            "message": redact_secrets(c.message),
                        }
                        for c in s.checks
                    ],
                }
                for s in sections
            ],
            "summary": summary,
        }


def main():
    parser = argparse.ArgumentParser(description="Weft validation script")
    parser.add_argument("--quick", action="store_true", help="Quick mode (skip slow checks)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--section", help="Run specific section (A, B, C, D, E)")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow uncommitted changes")
    parser.add_argument("--no-tests", action="store_true", help="Skip test execution")

    args = parser.parse_args()

    validator = WeftValidator(args)
    result = validator.run()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Pretty print
        for section in result["sections"]:
            print(f"\n{section['name']}")
            print("=" * 60)
            for check in section["checks"]:
                status_symbol = {"pass": "✓", "fail": "✗", "warn": "⚠", "skip": "-"}[
                    check["status"]
                ]
                print(f"  {status_symbol} {check['name']}: {check['message']}")

        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total:   {result['summary']['total']}")
        print(f"Passed:  {result['summary']['passed']}")
        print(f"Failed:  {result['summary']['failed']}")
        print(f"Warned:  {result['summary']['warned']}")
        print(f"Skipped: {result['summary']['skipped']}")

    # Exit code: 0 if all passed, 1 if any failed
    sys.exit(1 if result["summary"]["failed"] > 0 else 0)


if __name__ == "__main__":
    main()
