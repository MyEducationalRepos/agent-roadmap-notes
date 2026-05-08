"""Tool registry and dispatcher for the Phase 1a agent."""

import os
from pathlib import Path

from tavily import TavilyClient

TOOLS = []

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
	raise NotImplementedError()
