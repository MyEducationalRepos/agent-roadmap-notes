# CLAUDE.md — Active State Hub

> Project: agent-from-scratch (Phase 1a)
> Generated: 2026-05-08
> Source: architecture.md + tasks.md
> Focus: full MVP

---

## Execution Table

| # | Task | Thought (z) | Action (a) | Validator (v) | Status | Commit |
|---|------|-------------|------------|---------------|--------|--------|
| T-001 | Initialise uv project with `pyproject.toml` | Establishes the dependency graph and build backend (hatchling). All downstream tasks depend on this. ARM note: `anthropic` and `tavily-python` ship pure-Python wheels — no native binary risk on M-series. | `cd phase_01-a && uv venv .venv --python 3.12 && uv pip install -e ".[dev]"` | `python -c "import anthropic, tavily, dotenv, pytest; print('OK')"` | Success | `chore(bootstrap): init uv project with pyproject.toml` |
| T-002 | Create `.env.example` and `.gitignore` | Prevents secret leakage and unintentional artefact commits. Critical: `.env` must never reach git. ARM note: no platform-specific concern. | `touch .env.example .gitignore` then populate both files per architecture § 3 | `git check-ignore .env && git check-ignore out.md && grep ANTHROPIC_API_KEY .env.example` | Success | `chore(config): add .env.example and .gitignore` |
| T-003 | Create stub modules `agent.py` and `tools.py` | Establishes the two-module boundary (loop vs. tool logic) defined in architecture § 2. Stubs let later tasks focus on single responsibilities. ARM note: stdlib only. | `touch agent.py tools.py` then add docstrings, `TOOLS=[]`, and `dispatch` stub (raises `NotImplementedError`) | `python -m py_compile agent.py && python -m py_compile tools.py` | Success | `chore(scaffold): add agent.py and tools.py stubs` |
| T-004 | Implement `read_file(path) -> str` | Implements US-005. Uses only stdlib `open()`. Must never raise — errors are returned as strings per architecture § 6 tool result contract. ARM note: no native dependency. | Write `read_file` in `tools.py`; create `tests/test_tools.py` with `test_read_file_exists`, `test_read_file_missing`, `test_read_file_binary` | `uv run pytest tests/test_tools.py::test_read_file_exists tests/test_tools.py::test_read_file_missing tests/test_tools.py::test_read_file_binary -v` | Success | `feat(tools): implement read_file with error returns` |
| T-005 | Implement `write_file(path, content) -> str` | Implements US-006. Creates/overwrites target file; detects missing parent dir before writing. Never raises. ARM note: stdlib only. | Add `write_file` to `tools.py`; add `test_write_file_creates` and `test_write_file_bad_dir` to `tests/test_tools.py` | `uv run pytest tests/test_tools.py::test_write_file_creates tests/test_tools.py::test_write_file_bad_dir -v` | Success | `feat(tools): implement write_file with error returns` |
| T-006 | Implement `web_search(query) -> str` | Implements US-004. Module-level `TavilyClient` init provides fail-fast on missing API key. All exceptions caught and returned as error strings. ARM note: `tavily-python` is pure Python; no wheel risk. | Add `web_search` to `tools.py`; add `test_web_search_mock` and `test_web_search_api_error` to `tests/test_tools.py` using `pytest-mock` | `uv run pytest tests/test_tools.py::test_web_search_mock tests/test_tools.py::test_web_search_api_error -v` | Success | `feat(tools): implement web_search with Tavily client` |
| T-007 | Define `TOOLS` list (3 JSON schemas) | Architecture § 3 requires `TOOLS` as a module-level constant exported from `tools.py`. The schemas are consumed directly by `client.messages.create`. ARM note: no concern. | Add `TOOLS: list[dict]` constant to `tools.py` with 3 Anthropic tool definition dicts; add `test_tools_schema` to `tests/test_tools.py` | `uv run pytest tests/test_tools.py::test_tools_schema -v` | Success | `feat(tools): define TOOLS list with 3 JSON schemas` |
| T-008 | Implement `dispatch(name, args, tool_use_id) -> dict` | Implements US-008. Strategy pattern over `_HANDLERS` dict. Wraps every call in `try/except` so no tool error propagates to the loop. Returns `is_error: True` for unknown names and exceptions. ARM note: no concern. | Add `dispatch` implementation to `tools.py`; add `test_dispatch_write_roundtrip`, `test_dispatch_unknown`, `test_dispatch_exception` to `tests/test_tools.py` | `uv run pytest tests/test_tools.py -v` (all 10 tests green) | Success | `feat(tools): implement dispatch with error wrapping` |
| T-009 | Implement env loading, client init, constants | Implements US-001 startup. `load_dotenv()` must be first; `anthropic.Anthropic()` reads key from env automatically; fail-fast if `TAVILY_API_KEY` missing. ARM note: `anthropic` SDK is pure Python. | Add imports, `load_dotenv()`, `client`, `MODEL`, `MAX_TURNS`, `MAX_RESULT_CHARS`, `DEFAULT_TASK` to `agent.py`; leave `__main__` block as `pass` | `python agent.py` (exit 0, no KeyError); then `unset ANTHROPIC_API_KEY && python agent.py` (expect error); restore key | Pending | `feat(agent): add env loading and client init` |
| T-010 | Messages list init and single-turn skeleton | First live API call. Validates that `TOOLS` schema and auth are correct. No loop yet — keeps the change atomic. ARM note: HTTPS only, no native lib. | Add `messages` init and single `client.messages.create` call to `agent.py`; print `stop_reason` | `python agent.py 2>&1 \| grep "stop_reason"` (must print one line) | Pending | `feat(agent): add single-turn messages call` |
| T-011 | Wrap call in `while` loop with `end_turn` and `max_tokens` branches | Implements US-003. Loop exits cleanly on `end_turn` (prints `=== DONE ===`) or bails out after `MAX_TURNS`. Prevents runaway API spend. ARM note: no concern. | Replace single-call block in `agent.py` with `for turn in range(1, MAX_TURNS+1)` loop; add `end_turn`, `max_tokens`, and `else` branches | `python agent.py 2>&1 \| grep "=== DONE ==="` (must match) | Pending | `feat(agent): add agentic loop with exit branches` |
| T-012 | Implement `tool_use` branch with parallel dispatch | Implements US-007. All `tool_use` blocks dispatched in one list comprehension; results sent as a single `user` message — Anthropic parallel tool call contract. Add mandatory comment. ARM note: no concern. | Add `elif response.stop_reason == "tool_use":` block to loop in `agent.py` with parallel dispatch and single combined result message | `python agent.py 2>&1 \| grep -c "tool_use_id"` (≥ 1) | Pending | `feat(agent): implement parallel tool_use dispatch` |
| T-013 | Implement trace printing | Implements US-002. Prints `--- Step N ---`, `stop_reason`, each tool name + truncated input, each tool result truncated to `MAX_RESULT_CHARS`. No logging framework — plain `print()`. ARM note: no concern. | Add `print(f"--- Step {turn} ---")` and per-tool trace prints inside the loop in `agent.py` | `python agent.py 2>&1 \| grep -E "^--- Step [0-9]+ ---"` (≥ 1 match) && `grep "tool:" <(python agent.py 2>&1)` | Pending | `feat(agent): add step trace to stdout` |
| T-014 | Behaviour validation — run agent end-to-end | Implements runtime acceptance of US-001, US-002, US-003, US-006. Unit tests are necessary but not sufficient — behaviour must be confirmed with live APIs. ARM note: no concern. | `python agent.py 2>&1 \| tee trace.txt` | `grep -c "^--- Step" trace.txt && grep "=== DONE ===" trace.txt && wc -c < out.md \| awk '$1>=100' && echo "exit: $?"` | Pending | `test(integration): confirm agent end-to-end trace` |
| T-015 | Verify `agent.py` ≤ 100 lines | US-001 hard constraint. If over budget, move helper structures to `tools.py` rather than deleting explanatory comments (required by US-007). ARM note: no concern. | `wc -l agent.py` | `wc -l agent.py \| awk '{if ($1>100) {print "FAIL: "$1" lines"; exit 1} else print "OK: "$1" lines"}'` | Pending | `refactor(agent): trim to ≤100 lines` |
| T-016 | Write README `stop_reason values` section | Implements US-009. Must list all 4 values: `end_turn`, `tool_use`, `max_tokens`, `stop_sequence`. Cross-check against Anthropic API reference before writing. ARM note: docs only. | Add `## stop_reason values` section to `README.md` with table + `if/elif` snippet copied from `agent.py` | `grep "## stop_reason values" README.md && grep -c "end_turn\|tool_use\|max_tokens\|stop_sequence" README.md \| awk '$1>=4'` | Pending | `docs(readme): add stop_reason values reference` |
| T-017 | Add `Parallel tool calls` section to README | Implements US-010. ≤ 200 words. Includes sequential-vs-parallel before/after example. References the comment in `agent.py`. ARM note: docs only. | Add `## Parallel tool calls` section to `README.md` | `grep "## Parallel tool calls" README.md && awk '/^## Parallel/,/^## /' README.md \| wc -w \| awk '$1<=220'` | Pending | `docs(readme): add parallel tool calls explanation` |
| T-018 | Add `Tool error handling` section to README | Implements US-011. Three points: per-tool catch, `is_error: true`, model decides retry. Concrete trace example for `web_search` failure. ARM note: docs only. | Add `## Tool error handling` section to `README.md` with fenced trace example | `grep "## Tool error handling" README.md && grep "is_error" README.md` | Pending | `docs(readme): add tool error handling policy` |
| T-019 | Write README introduction and setup sections | Implements US-001 runability requirement. A new reader must be able to clone + run with no prior knowledge. ARM note: mention that `uv` and Python 3.12 must be installed; no arch-specific setup needed. | Add title, description, Prerequisites, Installation, and Usage sections to `README.md` | `grep "python agent.py" README.md && grep "uv venv" README.md` | Pending | `docs(readme): add intro and setup guide` |

---

## Notes

### One-time environment setup (run once per machine)

```bash
# From phase_01-a/
uv venv .venv
source .venv/bin/activate          # or .venv/Scripts/activate on Windows
uv pip install -e ".[dev]"
cp .env.example .env               # then fill in real API keys — never commit .env
```

### Running tests

```bash
uv run pytest tests/ -v            # unit tests only — no API keys required
```

### Running the agent (requires live API keys)

```bash
python agent.py 2>&1 | tee trace.txt
```

### ARM / Apple Silicon (M-series) notes

All dependencies (`anthropic`, `tavily-python`, `python-dotenv`, `pytest`, `pytest-mock`) ship pure-Python wheels. No compiled extension, no Docker base image, no native binary is involved in Phase 1a. `uv` resolves wheels correctly on `arm64` macOS without any extra flags.

### Commit discipline

- One commit per task, only after its Validator passes
- Conventional Commits format: `type(scope): short imperative message`
- Never commit `.env`, `out.md`, `trace.txt`, or `.venv/`
