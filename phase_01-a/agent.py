"""CLI entry point for the Phase 1a agent."""

import os
import sys

import anthropic
from dotenv import load_dotenv

from tools import TOOLS, dispatch

load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
	sys.exit("Error: ANTHROPIC_API_KEY not set")
if not os.environ.get("TAVILY_API_KEY"):
	sys.exit("Error: TAVILY_API_KEY not set")

client = anthropic.Anthropic()
MODEL = os.environ.get("MODEL", "claude-sonnet-4-5")
MAX_TURNS = int(os.environ.get("MAX_TURNS", "10"))
MAX_RESULT_CHARS = int(os.environ.get("MAX_RESULT_CHARS", "500"))
DEFAULT_TASK = (
	"Search the web for a brief overview of the Anthropic tool use API, "
	"then write a concise summary to out.md."
)


if __name__ == "__main__":
	pass
