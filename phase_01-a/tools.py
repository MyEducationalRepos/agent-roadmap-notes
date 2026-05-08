"""Tool registry and dispatcher for the Phase 1a agent."""

from pathlib import Path

TOOLS = []


def read_file(path):
	try:
		return Path(path).read_text(encoding="utf-8")
	except FileNotFoundError:
		return f"Error: file not found – {path}"
	except UnicodeDecodeError:
		return "Error: not a text file"


def dispatch(name, args, tool_use_id):
	raise NotImplementedError()
