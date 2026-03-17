I will use qwen3-coder-plus.

Agent structure:
The agent will be extended in agent.py to implement the full agentic loop with two tools: read_file and list_files. The tools will be defined as function-calling schemas and registered in the LLM request. The agentic loop will send the user question and tool definitions to the LLM, execute tools if the LLM responds with tool_calls, append results as tool role messages, and repeat until the LLM returns a text message or 10 tool calls are reached. The final answer and source will be extracted and output as JSON.

Tool schemas:
read_file(path: string) reads a file from the project repository and returns file contents as a string or an error message if the file does not exist.
list_files(path: string) lists files and directories at a given path and returns a newline-separated listing of entries.

Path security:
Both tools will validate that the requested path does not escape the project root directory. Paths will be resolved using Path.resolve() and checked against the project root prefix to prevent ../ traversal.

System prompt strategy:
The system prompt will instruct the LLM to use list_files to discover wiki files in the wiki directory, use read_file to read relevant files and find the answer, and include a source reference in the final answer with file path and section anchor.

Output format:
The CLI will output a single JSON line with three required fields: answer as the final answer string, source as the wiki section reference, and tool_calls as an array of all tool calls with tool, args, and result fields.

Configuration:
LLM API credentials will be read from the .env.agent.secret file, same as Task 1.
