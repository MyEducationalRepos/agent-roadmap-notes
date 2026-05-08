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
