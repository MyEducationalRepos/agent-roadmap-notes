"""Tool registry and dispatcher for the Phase 1a agent."""

import os
from pathlib import Path

from tavily import TavilyClient

TOOLS = [
	{
		"name": "web_search",
		"description": "Search the web via Tavily and return up to 5 results as plain text.",
		"input_schema": {
			"type": "object",
			"properties": {
				"query": {"type": "string", "description": "Search query"},
			},
			"required": ["query"],
		},
	},
	{
		"name": "read_file",
		"description": "Read a UTF-8 text file from disk and return its contents.",
		"input_schema": {
			"type": "object",
			"properties": {
				"path": {"type": "string", "description": "Filesystem path to read"},
			},
			"required": ["path"],
		},
	},
	{
		"name": "write_file",
		"description": "Write UTF-8 text to a file, creating or overwriting it.",
		"input_schema": {
			"type": "object",
			"properties": {
				"path": {"type": "string", "description": "Filesystem path to write"},
				"content": {"type": "string", "description": "Text content to write"},
			},
			"required": ["path", "content"],
		},
	},
]

_tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"]) if os.environ.get("TAVILY_API_KEY") else None


def web_search(query):
	if _tavily is None:
		return "Error: TAVILY_API_KEY not set"
	try:
		response = _tavily.search(query=query, max_results=5)
		results = response.get("results", []) if isinstance(response, dict) else []
		if not results:
			return "No results"
		return "\n\n".join(
			f"{item.get('title', '')}\n{item.get('url', '')}\n{item.get('content', '')}"
			for item in results
		)
	except Exception as error:
		return f"Error: web search failed – {error}"


def read_file(path):
	try:
		return Path(path).read_text(encoding="utf-8")
	except FileNotFoundError:
		return f"Error: file not found – {path}"
	except UnicodeDecodeError:
		return "Error: not a text file"


def write_file(path, content):
	file_path = Path(path)
	if not file_path.parent.exists():
		return f"Error: parent directory not found – {file_path.parent}"
	try:
		file_path.write_text(content, encoding="utf-8")
		return f"OK: wrote file – {path}"
	except OSError as error:
		return f"Error: could not write file – {error}"


def dispatch(name, args, tool_use_id):
	handler = _HANDLERS.get(name)
	if handler is None:
		return {
			"type": "tool_result",
			"tool_use_id": tool_use_id,
			"content": f"Error: unknown tool – {name}",
			"is_error": True,
		}
	try:
		content = handler(**args)
		is_error = isinstance(content, str) and content.startswith("Error:")
		return {
			"type": "tool_result",
			"tool_use_id": tool_use_id,
			"content": content,
			"is_error": is_error,
		}
	except Exception as error:
		return {
			"type": "tool_result",
			"tool_use_id": tool_use_id,
			"content": f"Error: tool raised – {error}",
			"is_error": True,
		}


_HANDLERS = {
	"web_search": web_search,
	"read_file": read_file,
	"write_file": write_file,
}
