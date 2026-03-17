# Agent CLI — Documentation

## Overview

This project implements a command-line interface (CLI) agent (`agent.py`) that accepts questions from the user, sends them to a Large Language Model (LLM), and returns a structured response in JSON format. The agent has tools to interact with the project repository and implements an agentic loop for multi-step reasoning.

## Quick Start

### 1. Set Up the Environment

Create a configuration file for the LLM:

```bash
cp .env.agent.example .env.agent.secret
```

Edit the `.env.agent.secret` file and fill in the required parameters:

- `LLM_API_KEY` — your API key from the LLM provider
- `LLM_API_BASE` — base URL of the API endpoint
- `LLM_MODEL` — name of the model to use

### 2. Run the Agent

```bash
uv run agent.py "Your question here"
```

### 3. Example Output

```json
{"answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.", "source": "wiki/git-workflow.md#resolving-merge-conflicts", "tool_calls": [{"tool": "list_files", "args": {"path": "wiki"}, "result": "git-workflow.md"}, {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}]}
```

## LLM Provider

**Provider:** Qwen Code API (deployed on VM)

**Model:** `qwen3-coder-plus`

**Configuration:**

- `LLM_API_KEY` — API key for authentication
- `LLM_API_BASE` — OpenAI-compatible endpoint URL (example: `http://10.93.25.160:42005/v1`)
- `LLM_MODEL` — model name (`qwen3-coder-plus`)

## Architecture

### Component Flow

```
User CLI → agent.py → VM Proxy (port 42005) → Qwen Cloud LLM
```

### How It Works

1. **Input Parsing** — the agent reads the question from the first command-line argument
2. **Configuration Loading** — LLM credentials are loaded from `.env.agent.secret`
3. **Agentic Loop** — the agent sends the question with tool definitions to the LLM, executes tool calls, and repeats until the LLM returns a final answer
4. **Response Formatting** — the final answer is wrapped in a JSON object with `answer`, `source`, and `tool_calls` fields
5. **Output** — a single JSON line is printed to stdout

### Output Routing

- **stdout** — only the final JSON response
- **stderr** — all debug, progress, and error messages

This separation allows the agent to be used in pipelines and scripts that parse JSON output.

## Tools

The agent has two tools for navigating the project repository.

### read_file

Reads the contents of a file from the project repository.

**Parameters:**
- `path` (string, required) — relative path to the file from project root

**Returns:** File contents as a string, or an error message if the file does not exist or cannot be read.

**Security:** The tool validates that the requested path does not escape the project root directory. Path traversal attempts using `../` are blocked.

### list_files

Lists files and directories at a given path.

**Parameters:**
- `path` (string, required) — relative path to the directory from project root

**Returns:** Newline-separated listing of file and directory names, or an error message if the directory does not exist.

**Security:** The tool validates that the requested path does not escape the project root directory. Path traversal attempts using `../` are blocked.

## Agentic Loop

The agentic loop enables multi-step reasoning by iteratively calling tools and feeding results back to the LLM.

### Loop Steps

1. Send the user's question and tool definitions to the LLM
2. If the LLM responds with tool calls, execute each tool and append results as tool role messages
3. Send the updated message history back to the LLM
4. Repeat until the LLM returns a text message (no tool calls) or 10 tool calls are reached
5. Extract the final answer and source reference from the response

### Maximum Tool Calls

The agent stops after 10 tool calls to prevent infinite loops. If this limit is reached, the agent returns whatever answer it has gathered so far.

### System Prompt Strategy

The system prompt instructs the LLM to use `list_files` to discover wiki files in the `wiki` directory, then use `read_file` to read relevant files and find the answer. The LLM is also instructed to include a source reference in the final answer with file path and section anchor.

## Project Structure

```
se-toolkit-lab-6/
├── agent.py              # Main CLI script
├── .env.agent.example    # Configuration template
├── .env.agent.secret     # Actual configuration (gitignored)
├── AGENT.md              # This documentation
├── wiki/                 # Project documentation wiki
└── backend/tests/        # Agent tests
```

## Input and Output Specification

### Input

One command-line argument containing the question:

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

### Output

A single JSON line with three required fields:

```json
{"answer": "Edit the conflicting file...", "source": "wiki/git-workflow.md#resolving-merge-conflicts", "tool_calls": [...]}
```

**Fields:**

- `answer` (string) — the final answer extracted from the LLM response
- `source` (string) — the wiki section reference (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`)
- `tool_calls` (array) — all tool calls made during the agentic loop, each with `tool`, `args`, and `result` fields

## Error Handling

The agent exits with code 1 and prints an error message to stderr in the following cases:

- Missing `.env.agent.secret` file
- Missing required environment variables (`LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`)
- HTTP errors (4xx, 5xx) from the LLM provider
- Request timeout (exceeds 60 seconds)
- Network errors during the request
- File access errors (file not found, permission denied)

On successful execution, the agent exits with code 0.

## Testing

Run the regression tests:

```bash
uv run pytest test_agent.py -v
```

The tests verify:

- `agent.py` executes successfully
- Output is valid JSON
- Required fields `answer`, `source`, and `tool_calls` are present
- Tool calls are logged correctly

## Requirements

- Python 3.10+
- Package manager `uv`
- Access to Qwen Code API (or compatible LLM provider)
- Configured `.env.agent.secret` file

## License

This project is part of a software engineering educational course.
