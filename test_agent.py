import json
import subprocess
import sys
from pathlib import Path


def test_agent_outputs_valid_json_with_required_fields() -> None:
    project_root = Path(__file__).parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, f"agent.py failed with: {result.stderr}"

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"agent.py output is not valid JSON: {result.stdout}") from e

    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"
    assert output["answer"], "'answer' field should not be empty"


def test_agent_uses_read_file_for_merge_conflict_question() -> None:
    project_root = Path(__file__).parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, f"agent.py failed with: {result.stderr}"

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"agent.py output is not valid JSON: {result.stdout}") from e

    assert "answer" in output, "Missing 'answer' field in output"
    assert "source" in output, "Missing 'source' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    tool_names = [call.get("tool") for call in output["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file to be called"

    assert "wiki/git-workflow.md" in output["source"], "Expected wiki/git-workflow.md in source"


def test_agent_uses_list_files_for_wiki_directory_question() -> None:
    project_root = Path(__file__).parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), "What files are in the wiki?"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, f"agent.py failed with: {result.stderr}"

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"agent.py output is not valid JSON: {result.stdout}") from e

    assert "answer" in output, "Missing 'answer' field in output"
    assert "source" in output, "Missing 'source' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    tool_names = [call.get("tool") for call in output["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files to be called"
