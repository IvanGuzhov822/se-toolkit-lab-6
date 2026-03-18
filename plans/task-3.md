I will use qwen3-coder-plus.

Agent structure:
The agent will be extended in agent.py to add a new query_api tool alongside the existing read_file and list_files tools. The query_api tool will send HTTP requests to the deployed backend API and return JSON responses with status_code and body fields. The agentic loop will remain the same — the LLM can now choose between three tools based on the question type.

Tool schema for query_api:
The query_api tool will be defined as a function-calling schema with three parameters: method (string — HTTP method like GET, POST, PUT, DELETE), path (string — API endpoint path like /items/ or /analytics/completion-rate), and body (string, optional — JSON request body for POST/PUT requests). The tool will return a JSON string containing status_code and body from the HTTP response.

Authentication handling:
The query_api tool will authenticate requests using the LMS_API_KEY environment variable read from .env.docker.secret. This key will be sent in the Authorization header as "Bearer <LMS_API_KEY>" for all API requests. The LLM API key (LLM_API_KEY from .env.agent.secret) is separate and only used for LLM provider authentication — these two keys must not be confused.

Configuration:
The agent will read LMS_API_KEY from .env.docker.secret and AGENT_API_BASE_URL from environment (defaulting to http://localhost:42002 if not set). The AGENT_API_BASE_URL points to the Caddy reverse proxy that forwards requests to the backend. All configuration must come from environment variables — no hardcoded values — so the autochecker can inject its own credentials during evaluation.

System prompt update:
The system prompt will be updated to instruct the LLM on when to use each tool category. For wiki/documentation questions (e.g., "According to the project wiki..."), use read_file and list_files to search the wiki directory. For system facts (e.g., "What framework does the backend use?"), use read_file on source code files. For data-dependent queries (e.g., "How many items are in the database?", "What status code does /items/ return?"), use query_api to query the running backend. For bug diagnosis questions, first use query_api to reproduce the error, then use read_file on the relevant source code to identify the bug.

Path security:
The existing path validation for read_file and list_files will remain unchanged — both tools validate that requested paths do not escape the project root directory using Path.resolve() and prefix checking.

Output format:
The CLI will continue to output a single JSON line with answer, source (optional for system questions), and tool_calls fields. The tool_calls array will now include query_api calls with method, path, body, and result fields.

Benchmark iteration strategy:
After implementing query_api, I will run uv run run_eval.py to test against all 10 local questions. For each failing question, I will analyze the feedback to identify whether the issue is: tool not being called (improve tool description in schema), tool returning errors (fix implementation), wrong arguments (clarify parameter descriptions), or answer phrasing (adjust system prompt). I will iterate until all questions pass.
