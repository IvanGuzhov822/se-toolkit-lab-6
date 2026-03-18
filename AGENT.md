# Agent CLI — Documentation

## Overview

This project implements a command-line interface agent that accepts questions from the user, sends them to a Large Language Model, and returns a structured response in JSON format. The agent has tools to interact with the project repository and the deployed backend API, implementing an agentic loop for multi-step reasoning. The agent can answer wiki documentation questions, system fact questions, data-dependent queries, and bug diagnosis questions by selecting the appropriate tool based on the question type.

## Quick Start

Create a configuration file for the LLM by copying .env.agent.example to .env.agent.secret and filling in the required parameters: LLM_API_KEY for your LLM provider API key, LLM_API_BASE for the API endpoint URL, and LLM_MODEL for the model name. Then run the agent with uv run agent.py followed by your question in quotes. The agent outputs a single JSON line with answer, source, and tool_calls fields.

## LLM Provider

The agent uses Qwen Code API deployed on a VM with the qwen3-coder-plus model. Configuration is read from .env.agent.secret with three variables: LLM_API_KEY for authentication, LLM_API_BASE for the OpenAI-compatible endpoint URL, and LLM_MODEL for the model name.

## Architecture

The component flow goes from User CLI to agent.py to VM Proxy on port 42005 to Qwen Cloud LLM. The agent reads the question from the command line, loads LLM credentials from .env.agent.secret, sends the question with tool definitions to the LLM, executes tool calls if any, and repeats until the LLM returns a final answer. The final answer is wrapped in JSON with answer, source, and tool_calls fields. Only the final JSON response goes to stdout while all debug and error messages go to stderr.

## Tools

The agent has three tools for navigating the project repository and querying the backend API.

The read_file tool reads the contents of a file from the project repository. It takes a path parameter as a string representing the relative path from project root. It returns file contents as a string or an error message if the file does not exist. The tool validates that the requested path does not escape the project root directory and blocks path traversal attempts.

The list_files tool lists files and directories at a given path. It takes a path parameter as a string representing the relative directory path from project root. It returns a newline-separated listing of entries or an error message if the directory does not exist. The tool validates paths the same way as read_file.

The query_api tool sends HTTP requests to the deployed backend API. It takes method as a string for the HTTP method like GET, POST, PUT, or DELETE, path as a string for the API endpoint like /items/ or /analytics/completion-rate, and an optional body string for JSON request body on POST or PUT requests. It returns a JSON string with status_code and body fields. The tool authenticates using the LMS_API_KEY environment variable from .env.docker.secret, sending it as a Bearer token in the Authorization header. The API base URL is read from AGENT_API_BASE_URL environment variable, defaulting to http://localhost:42002.

## Configuration

All configuration is read from environment variables, not hardcoded values. The LLM configuration comes from .env.agent.secret with LLM_API_KEY, LLM_API_BASE, and LLM_MODEL. The backend API configuration comes from .env.docker.secret with LMS_API_KEY for authentication. The AGENT_API_BASE_URL can be set as an environment variable and defaults to http://localhost:42002 if not provided.

## Agentic Loop

The agentic loop enables multi-step reasoning by iteratively calling tools and feeding results back to the LLM. The agent sends the user question and tool definitions to the LLM. If the LLM responds with tool calls, the agent executes each tool and appends results as toFol role messages. The updated message history goes back to the LLM. This repeats until the LLM returns a text message with no tool calls or until 10 tool calls are reached. The agent then extracts the final answer and source reference from the response.

## System Prompt Strategy

The system prompt instructs the LLM on when to use each tool category. For wiki or documentation questions like questions mentioning the project wiki, the LLM should use list_files to discover wiki files in the wiki directory, then use read_file to read relevant files and include a source reference with file path and section anchor. For system facts like what framework the backend uses or what port the API runs on, the LLM should use read_file to examine source code files like backend/main.py, docker-compose.yml, or configuration files. For data-dependent queries like how many items are in the database or what status code an endpoint returns, the LLM should use query_api to send HTTP requests to the running backend. For bug diagnosis questions, the LLM should first use query_api to reproduce the error, then use read_file on the relevant source code to identify the bug.

## Input and Output Specification

Input is one command-line argument containing the question. Output is a single JSON line with three fields. The answer field contains the final answer string. The source field contains the wiki section reference for documentation questions. The tool_calls array contains all tool calls made during the agentic loop, each with tool, args, and result fields.

## Error Handling

The agent exits with code 1 and prints an error message to stderr for missing configuration files, missing environment variables, HTTP errors from the LLM provider, request timeouts, network errors, and file access errors. On successful execution, the agent exits with code 0.

## Testing

Run the regression tests with uv run pytest test_agent.py -v. The tests verify that agent.py executes successfully, output is valid JSON, required fields are present, and tool calls are logged correctly. Additional tests verify that the agent uses the correct tools for different question types.

## Lessons Learned

Building this agent revealed several important patterns. First, the LLM may return null for the content field when making tool calls, so the code must use (content or "") instead of relying on default values. Second, having clear tool descriptions in the function-calling schema is critical for the LLM to choose the right tool for each question type. Third, separating LLM authentication from backend API authentication prevents confusion and security issues. Fourth, the system prompt must explicitly guide the LLM on when to use each tool category, otherwise the LLM may try to use read_file for API queries or vice versa. Fifth, the LMS_API_KEY must be loaded from .env.docker.secret into environment variables so the query_api tool can access it. Sixth, for counting questions like "How many items...", the system prompt must explicitly instruct the LLM to call query_api and then COUNT the elements in the returned JSON array — just calling the API is not enough. Seventh, for bug diagnosis questions, the system prompt must tell the LLM to first reproduce the error via query_api to see the actual error type (ZeroDivisionError, TypeError), then read the source code to find the specific buggy line. Eighth, the query_api tool description should include explicit examples of endpoints like /items/, /learners/, and /analytics/completion-rate?lab=lab-XX to help the LLM understand which endpoints to use for different questions. Ninth, Windows console encoding issues can crash the agent when reading files with emoji characters — the fix is to wrap sys.stdout with UTF-8 encoding using io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'). Tenth, increasing the LLM timeout from 60 to 120 seconds prevents timeouts on multi-step questions that require several tool calls. Eleventh, the system prompt must explicitly tell the LLM to NEVER answer wiki/git/SSH/Docker questions from its own knowledge — always use read_file to find answers in project files. Twelfth, the analytics.py router has two specific bugs that the agent must identify: ZeroDivisionError in /completion-rate (division when total_learners is 0) and TypeError in /top-learners (sorted() comparing None values in avg_score). Thirteenth, the query_api tool description must explicitly explain that the body field is a JSON string that needs to be parsed, and for counting questions the LLM should count elements in the JSON array using len(array) — without this instruction, the LLM might guess or report incorrect counts like "0 items" when the array is actually non-empty but the LLM didn't parse it correctly.

## Requirements

Python 3.10 or higher, the uv package manager, access to Qwen Code API or compatible LLM provider, and a configured .env.agent.secret file.

## License

This project is part of a software engineering educational course.
