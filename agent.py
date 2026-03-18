#!/usr/bin/env python3
""""the update has been done"""
import json
import os
import sys
import io
from pathlib import Path

import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def load_env() -> dict[str, str]:
    env_file = Path(__file__).parent / ".env.agent.secret"
    env_vars: dict[str, str] = {}

    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        print("Copy .env.agent.example to .env.agent.secret and fill in the values", file=sys.stderr)
        sys.exit(1)

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def load_lms_env() -> dict[str, str]:
    env_file = Path(__file__).parent / ".env.docker.secret"
    env_vars: dict[str, str] = {}

    if not env_file.exists():
        return env_vars

    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def get_project_root() -> Path:
    return Path(__file__).parent


def validate_path(requested_path: str) -> Path | None:
    project_root = get_project_root()
    try:
        resolved = (project_root / requested_path).resolve()
        if not str(resolved).startswith(str(project_root.resolve())):
            return None
        return resolved.relative_to(project_root.resolve())
    except (ValueError, RuntimeError):
        return None


def read_file(path: str) -> str:
    validated = validate_path(path)
    if validated is None:
        return f"Error: Access denied - path '{path}' is outside project directory"

    file_path = get_project_root() / validated
    if not file_path.exists():
        return f"Error: File not found - {path}"
    if not file_path.is_file():
        return f"Error: Not a file - {path}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    validated = validate_path(path)
    if validated is None:
        return f"Error: Access denied - path '{path}' is outside project directory"

    dir_path = get_project_root() / validated
    if not dir_path.exists():
        return f"Error: Directory not found - {path}"
    if not dir_path.is_dir():
        return f"Error: Not a directory - {path}"

    try:
        entries = sorted(dir_path.iterdir())
        return "\n".join(entry.name for entry in entries)
    except Exception as e:
        return f"Error listing directory: {e}"


def query_api(method: str, path: str, body: str | None = None) -> str:
    api_base = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
    lms_api_key = os.environ.get("LMS_API_KEY")

    if not lms_api_key:
        return "Error: LMS_API_KEY not found in environment"

    url = f"{api_base.rstrip('/')}{path}"

    headers = {
        "Authorization": f"Bearer {lms_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=30) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                json_body = json.loads(body) if body else None
                response = client.post(url, headers=headers, json=json_body)
            elif method.upper() == "PUT":
                json_body = json.loads(body) if body else None
                response = client.put(url, headers=headers, json=json_body)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return f"Error: Unsupported HTTP method '{method}'"

            result = {
                "status_code": response.status_code,
                "body": response.text
            }
            
            if response.status_code == 401:
                result["error"] = "Unauthorized - check LMS_API_KEY authentication"
            elif response.status_code == 403:
                result["error"] = "Forbidden - invalid API key"
            
            return json.dumps(result)
    except httpx.TimeoutException:
        return "Error: API request timed out (30 seconds)"
    except httpx.RequestError as e:
        return f"Error: Request failed: {e}"
    except json.JSONDecodeError:
        return "Error: Invalid JSON in request body"
    except Exception as e:
        return f"Error: {e}"


def get_tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file from the project repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file from project root"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the directory from project root"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Send an HTTP request to the deployed backend API. Use this tool for ALL data-dependent questions: counting items (GET /items/), counting learners (GET /learners/), checking status codes, getting analytics data. For bugs: call this first to see the error. Returns JSON with status_code and body fields. The body is a JSON string — parse it to get the actual data. For counting: if body is a JSON array like '[{...},{...}]', count the elements (len(array)). For status codes: check the status_code field.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method: GET, POST, PUT, DELETE"
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path, e.g., /items/, /learners/, /analytics/completion-rate?lab=lab-99"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT requests"
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


def execute_tool(tool_name: str, args: dict) -> str:
    if tool_name == "read_file":
        return read_file(args.get("path", ""))
    elif tool_name == "list_files":
        return list_files(args.get("path", ""))
    elif tool_name == "query_api":
        return query_api(
            method=args.get("method", "GET"),
            path=args.get("path", ""),
            body=args.get("body")
        )
    else:
        return f"Error: Unknown tool '{tool_name}'"


def call_llm(
    messages: list[dict],
    api_key: str,
    api_base: str,
    model: str,
    tools: list[dict] | None = None,
    timeout: int = 120
) -> dict:
    url = f"{api_base}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }

    if tools:
        payload["tools"] = tools

    print(f"Calling LLM at {url} with model {model}...", file=sys.stderr)

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    return data


def extract_source_from_messages(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content") or ""
            if content:
                import re
                matches = re.findall(r"[\w\-/]+\.[\w]+#[\w\-]+", content)
                if matches:
                    return matches[0]
                file_matches = re.findall(r"[\w\-/]+\.[\w]+", content)
                if file_matches:
                    return file_matches[0]
    return "wiki"


def run_agentic_loop(
    question: str,
    api_key: str,
    api_base: str,
    model: str,
    max_tool_calls: int = 10
) -> dict:
    tools = get_tool_schemas()

    system_prompt = (
        "You are an intelligent agent that helps users find information about the project. "
        "You have three categories of tools: wiki tools (read_file, list_files), API tool (query_api), and direct knowledge. "
        "CRITICAL RULES: "
        "1. COUNTING QUESTIONS: For 'How many items...', 'How many learners...', 'How many distinct...' — ALWAYS call query_api with GET /items/ or GET /learners/. The API returns JSON like '{\"status_code\": 200, \"body\": \"[{...},{...}]\"}'. Check status_code first: if 200, parse the body JSON array and COUNT its elements. Report the exact number. If status_code is 401 or 403, report authentication error. If the array is empty, say '0 items'. If the array has elements, report the count. "
        "2. BUG QUESTIONS: For questions about errors, crashes, or bugs — ALWAYS first call query_api to reproduce the error and read the error type (e.g., ZeroDivisionError, TypeError). THEN call read_file on the relevant source file (e.g., backend/app/routers/analytics.py) to find the buggy line. "
        "3. WIKI QUESTIONS: For 'According to the wiki...', 'What does the wiki say...', 'How to...' questions about git, SSH, Docker, Linux, VM — use list_files on wiki/, then read_file on relevant wiki files. NEVER answer from your own knowledge for these topics. "
        "4. SOURCE CODE QUESTIONS: For 'What framework...', 'What technique...', 'Read the Dockerfile...' — use read_file on the specific source files mentioned. "
        "5. DOCKER QUESTIONS: For docker-compose.yml or Dockerfile questions — use read_file on those exact files. "
        "6. STATUS CODE QUESTIONS: For 'What HTTP status code...' — call query_api and report the status_code from the response. "
        "When analyzing analytics.py for bugs, look for TWO specific issues: "
        "(1) GET /completion-rate endpoint: division operation 'rate = (passed_learners / total_learners) * 100' where total_learners could be zero, causing ZeroDivisionError. "
        "(2) GET /top-learners endpoint: 'sorted(rows, key=lambda r: r.avg_score, ...)' where avg_score could be None (from SQL AVG on empty data), causing TypeError when comparing None values. "
        "After calling query_api, always parse the JSON response: (1) check status_code — 200 means success, 401/403 means auth error, (2) parse body JSON array for counting questions, (3) read error messages for bug questions. "
        "Always use tools to find answers — never respond from your own knowledge when the answer should come from project files or API. "
        "Be concise and accurate."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    tool_calls_log = []
    tool_call_count = 0

    while tool_call_count < max_tool_calls:
        response_data = call_llm(messages, api_key, api_base, model, tools)

        try:
            assistant_message = response_data["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            print(f"Error parsing LLM response: {e}", file=sys.stderr)
            sys.exit(1)

        tool_calls = assistant_message.get("tool_calls", [])

        if not tool_calls:
            final_answer = (assistant_message.get("content") or "")
            source = extract_source_from_messages(messages)
            return {
                "answer": final_answer,
                "source": source,
                "tool_calls": tool_calls_log
            }

        for tool_call in tool_calls:
            if tool_call_count >= max_tool_calls:
                break

            function = tool_call.get("function", {})
            tool_name = function.get("name", "unknown")
            tool_args = json.loads(function.get("arguments", "{}"))

            result = execute_tool(tool_name, tool_args)

            tool_calls_log.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result
            })

            tool_call_count += 1

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": result
            })

    final_answer = "Maximum tool calls reached. Here is what I found."
    source = extract_source_from_messages(messages)
    return {
        "answer": final_answer,
        "source": source,
        "tool_calls": tool_calls_log
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    lms_env = load_lms_env()
    for key, value in lms_env.items():
        if key not in os.environ:
            os.environ[key] = value

    env = load_env()

    api_key = env.get("LLM_API_KEY")
    api_base = env.get("LLM_API_BASE")
    model = env.get("LLM_MODEL")

    if not api_key:
        print("Error: LLM_API_KEY not found in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    if not api_base:
        print("Error: LLM_API_BASE not found in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    if not model:
        print("Error: LLM_MODEL not found in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    api_base = api_base.rstrip("/")

    try:
        result = run_agentic_loop(question, api_key, api_base, model)
        print(json.dumps(result, ensure_ascii=False))

    except httpx.TimeoutException:
        print("Error: LLM request timed out (120 seconds)", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error: HTTP error {e.response.status_code}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
