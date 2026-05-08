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
	task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK
	messages = [{"role": "user", "content": task}]
	for turn in range(1, MAX_TURNS + 1):
		response = client.messages.create(
			model=MODEL,
			max_tokens=1024,
			tools=TOOLS,
			messages=messages,
		)
		print(f"stop_reason: {response.stop_reason}")
		if response.stop_reason == "end_turn":
			print("=== DONE ===")
			break
		elif response.stop_reason == "max_tokens":
			print("=== HALT: max_tokens ===")
			break
		elif response.stop_reason == "tool_use":
			# Parallel tool calls: dispatch every tool_use block in this turn
			# and return all results in a single user message — required by
			# the Anthropic tool-use contract.
			messages.append({"role": "assistant", "content": response.content})
			tool_results = [
				dispatch(block.name, block.input, block.id)
				for block in response.content
				if block.type == "tool_use"
			]
			for result in tool_results:
				print(f"tool_use_id={result['tool_use_id']} is_error={result['is_error']}")
			messages.append({"role": "user", "content": tool_results})
		else:
			print(f"=== HALT: unhandled stop_reason {response.stop_reason} ===")
			break
	else:
		print(f"=== HALT: MAX_TURNS={MAX_TURNS} reached ===")
