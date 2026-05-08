# MVP Task List

> Project: agent-from-scratch (Phase 1a)
> Generated: 2026-05-08
> Total tasks: 19

---

## Phase 1: Project Bootstrap

### T-001: Initialise uv project with `pyproject.toml`

**User story ref:** Architecture § 5 (Stack Summary, Docker & Deployment)
**Start condition:** Empty directory `agent-from-scratch/` exists.
**End condition:** `uv venv && uv pip install -e .` exits 0; `anthropic`, `tavily-python`, `python-dotenv` are importable; `pytest` available in dev.

**Test first:**
- [ ] Run `uv pip install -e ".[dev]"` — expect exit code 0
- [ ] Run `python -c "import anthropic, tavily, dotenv"` — expect no `ImportError`
- [ ] Run `python -c "import pytest"` — expect no `ImportError`

**Implementation notes:**
- Create `pyproject.toml` with exact content from Architecture § 5
- Use `hatchling` as build backend
- `requires-python = ">=3.12"`
- Run `uv venv` then `uv pip install -e ".[dev]"` to verify; never `pip`
- No `src/` layout — flat root

---

### T-002: Create `.env.example` and `.gitignore`

**User story ref:** Architecture § 3 (State Management), US-001
**Start condition:** `pyproject.toml` exists (T-001 done).
**End condition:** `.env.example` lists all 5 env vars with placeholder values; `.gitignore` excludes `.env`, `out.md`, `__pycache__/`, `.venv/`.

**Test first:**
- [ ] `cat .env.example | grep ANTHROPIC_API_KEY` — must match
- [ ] `cat .env.example | grep TAVILY_API_KEY` — must match
- [ ] `git check-ignore .env` — must print `.env`
- [ ] `git check-ignore out.md` — must print `out.md`

**Implementation notes:**
- `.env.example` entries: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `MODEL`, `MAX_TURNS`, `MAX_RESULTS_CHARS` — each with placeholder `=your_value_here`
- Do NOT commit `.env` — it is a secret file
- `.gitignore` pattern `out.md` (not `*.md` — README must remain tracked)

---

### T-003: Create stub modules `agent.py` and `tools.py`

**User story ref:** Architecture § 2 (File & Folder Structure)
**Start condition:** T-001 done; project root exists.
**End condition:** Both files exist, are valid Python (no syntax errors), and `python -c "import agent, tools"` succeeds with `PYTHONPATH=.`.

**Test first:**
- [ ] `python -m py_compile agent.py` — exit code 0
- [ ] `python -m py_compile tools.py` — exit code 0

**Implementation notes:**
- `agent.py`: module-level docstring only + `if __name__ == "__main__": pass`
- `tools.py`: module-level docstring + `TOOLS: list = []` + `def dispatch(name, args, tool_use_id): ...` (raise `NotImplementedError`)
- These are stubs only — no logic yet

---

## Phase 2: Tool Layer (`tools.py`)

### T-004: Implement `read_file(path: str) -> str`

**User story ref:** US-005
**Start condition:** `tools.py` stub exists (T-003 done).
**End condition:** Function returns UTF-8 file content on success; returns `"Error: file not found – <path>"` for missing files; returns `"Error: not a text file"` for binary content; never raises.

**Test first:**
- [ ] In `tests/test_tools.py`: `test_read_file_exists` — create `tmp_path/"fixture.txt"` with known content; assert `read_file(str(path)) == "known content"`
- [ ] `test_read_file_missing` — assert `read_file("/nonexistent/path.txt").startswith("Error: file not found")`
- [ ] `test_read_file_binary` — write `bytes([0x00, 0xFF])` to `tmp_path/"binary.bin"`; assert `read_file(str(path)) == "Error: not a text file"`
- [ ] Run `pytest tests/test_tools.py::test_read_file_exists tests/test_tools.py::test_read_file_missing tests/test_tools.py::test_read_file_binary -v` — all green

**Implementation notes:**
- `open(path, "r", encoding="utf-8")` inside `try/except FileNotFoundError`
- Catch `UnicodeDecodeError` to detect binary files
- Do not raise — all errors are return values (contract from Architecture § 6)
- File: `tools.py`, function `read_file`

---

### T-005: Implement `write_file(path: str, content: str) -> str`

**User story ref:** US-006
**Start condition:** `tools.py` has `read_file` (T-004 done).
**End condition:** Creates/overwrites file; returns `"OK: wrote N bytes to <path>"`; returns `"Error: directory not found – <path>"` when parent dir missing; never raises.

**Test first:**
- [ ] `test_write_file_creates` — call `write_file(str(tmp_path/"out.md"), "hello")` → assert return starts with `"OK: wrote"` and file exists with content `"hello"`
- [ ] `test_write_file_bad_dir` — call `write_file("/nonexistent/dir/out.md", "x")` → assert return starts with `"Error: directory not found"`
- [ ] Run `pytest tests/test_tools.py::test_write_file_creates tests/test_tools.py::test_write_file_bad_dir -v` — all green

**Implementation notes:**
- `open(path, "w", encoding="utf-8")` inside `try/except OSError`
- Use `os.path.dirname(path)` to detect missing parent directory before writing
- Return string `f"OK: wrote {len(content)} bytes to {path}"`
- File: `tools.py`, function `write_file`

---

### T-006: Implement `web_search(query: str) -> str`

**User story ref:** US-004
**Start condition:** T-005 done; `TAVILY_API_KEY` present in `.env`.
**End condition:** Returns formatted `"title\nurl\nsnippet\n"` string for ≥1 result; returns `"Error: Tavily – <message>"` on API error; never raises.

**Test first:**
- [ ] `test_web_search_mock` — use `pytest-mock` to patch `TavilyClient.search` returning `{"results": [{"title": "T", "url": "U", "content": "C"}]}`; assert `web_search("test")` contains `"T"` and `"U"`
- [ ] `test_web_search_api_error` — patch `TavilyClient.search` to raise `Exception("bad key")`; assert `web_search("test").startswith("Error: Tavily")`
- [ ] Run `pytest tests/test_tools.py::test_web_search_mock tests/test_tools.py::test_web_search_api_error -v` — all green

**Implementation notes:**
- Module-level `_tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])` — fails fast if key missing
- `try: results = _tavily.search(query)["results"] except Exception as e: return f"Error: Tavily – {e}"`
- Format: join per result as `f"{r['title']}\n{r['url']}\n{r['content']}\n"`
- File: `tools.py`, function `web_search`

---

### T-007: Define `TOOLS` list (3 JSON schemas)

**User story ref:** Architecture § 3 (State Management — `TOOLS` constant)
**Start condition:** T-006 done (all 3 functions implemented).
**End condition:** `tools.TOOLS` is a list of 3 dicts, each valid Anthropic tool definition with `name`, `description`, and `input_schema`.

**Test first:**
- [ ] `test_tools_schema` — `from tools import TOOLS`; assert `len(TOOLS) == 3`; assert `{t["name"] for t in TOOLS} == {"web_search", "read_file", "write_file"}`; assert each has `"input_schema"` key
- [ ] Run `pytest tests/test_tools.py::test_tools_schema -v` — green

**Implementation notes:**
- Each schema: `{"type": "function", "name": ..., "description": ..., "input_schema": {"type": "object", "properties": {...}, "required": [...]}}`
- `web_search`: property `query` (string, required)
- `read_file`: property `path` (string, required)
- `write_file`: properties `path` (string) and `content` (string), both required
- File: `tools.py`, module-level constant `TOOLS`

---

### T-008: Implement `dispatch(name, args, tool_use_id) -> dict`

**User story ref:** US-008, Architecture § 2 (Module responsibilities)
**Start condition:** T-007 done — all 3 functions and `TOOLS` exist.
**End condition:** `dispatch` returns a `tool_result` dict; unknown names return `is_error: True`; exceptions from any tool are caught and returned as `is_error: True`; never raises.

**Test first:**
- [ ] `test_dispatch_write_roundtrip` — call `dispatch("write_file", {"path": str(tmp_path/"x.md"), "content": "hi"}, "id-1")`; assert `result["type"] == "tool_result"` and `"OK" in result["content"]`
- [ ] `test_dispatch_unknown` — `dispatch("nonexistent", {}, "id-2")`; assert `result["is_error"] == True`
- [ ] `test_dispatch_exception` — patch `read_file` to `raise RuntimeError("boom")`; `dispatch("read_file", {"path": "x"}, "id-3")`; assert `result["is_error"] == True`
- [ ] Run `pytest tests/test_tools.py -v` — all 10 tests green

**Implementation notes:**
- Strategy pattern: `_HANDLERS = {"web_search": web_search, "read_file": read_file, "write_file": write_file}`
- Wrap handler call in `try/except Exception`
- Return shape: `{"type": "tool_result", "tool_use_id": tool_use_id, "content": str_result}` — add `"is_error": True` only on failure
- File: `tools.py`, function `dispatch`

---

## Phase 3: Agent Loop (`agent.py`)

### T-009: Implement env loading, client init, and constants

**User story ref:** US-001, Architecture § 4 (Auth flow)
**Start condition:** T-008 done; `.env` with real keys exists locally.
**End condition:** Running `python agent.py` loads env, instantiates `anthropic.Anthropic()` and `TavilyClient`, and exits 0 (with placeholder `pass` body below).

**Test first:**
- [ ] `python agent.py` with `.env` present — exit code 0, no `KeyError` or `AuthenticationError`
- [ ] Remove `ANTHROPIC_API_KEY` from env; `python agent.py` — raises `KeyError` or `AuthenticationError` (fail-fast)

**Implementation notes:**
- `from dotenv import load_dotenv; load_dotenv()` as first two lines
- `client = anthropic.Anthropic()` (reads `ANTHROPIC_API_KEY` automatically)
- Constants: `MODEL = os.getenv("MODEL", "claude-opus-4-5")`, `MAX_TURNS = int(os.getenv("MAX_TURNS", 10))`, `MAX_RESULT_CHARS = int(os.getenv("MAX_RESULT_CHARS", 500))`
- `DEFAULT_TASK` string: summarise `anthropic.com/engineering` last 5 posts to `out.md`
- File: `agent.py`

---

### T-010: Implement messages list init and single-turn skeleton

**User story ref:** US-001, Architecture § 3 (Messages list growth)
**Start condition:** T-009 done (env + constants in place).
**End condition:** `python agent.py` calls `client.messages.create` exactly once and prints the raw `stop_reason`; no loop yet.

**Test first:**
- [ ] Run `python agent.py 2>&1 | grep "stop_reason"` — must print one line containing `stop_reason`
- [ ] Run `python agent.py` — exit code 0

**Implementation notes:**
- `messages = [{"role": "user", "content": DEFAULT_TASK}]`
- Single call: `response = client.messages.create(model=MODEL, max_tokens=4096, tools=TOOLS, messages=messages)`
- Print `f"stop_reason: {response.stop_reason}"`
- No loop yet — that comes in T-011
- File: `agent.py`

---

### T-011: Wrap call in `while` loop with `end_turn` and `max_tokens` branches

**User story ref:** US-003, Architecture § 2 (agent.py loop logic)
**Start condition:** T-010 done — single-turn call works.
**End condition:** Loop runs until `stop_reason == "end_turn"` (prints `=== DONE ===` and breaks) or `turn >= MAX_TURNS` (prints informative bail-out message and breaks).

**Test first:**
- [ ] Run `python agent.py 2>&1 | grep "=== DONE ==="` — must match (if model reaches end_turn within MAX_TURNS)
- [ ] Mock `client.messages.create` to always return `stop_reason="max_tokens"` for 10 turns; assert loop exits with informative message (manual inspection or subprocess test)

**Implementation notes:**
- `for turn in range(1, MAX_TURNS + 1):` (or `while`); `turn` counter printed each step
- After `client.messages.create`: append assistant message to `messages`
- `if response.stop_reason == "end_turn": print("=== DONE ==="); break`
- `elif response.stop_reason == "max_tokens": print("Reached max_tokens — stopping."); break`
- `else: print(f"Unexpected stop_reason: {response.stop_reason}"); break`
- File: `agent.py`

---

### T-012: Implement `tool_use` branch with parallel dispatch

**User story ref:** US-007, US-008, Architecture § 2 (tool_use branch + parallel dispatch)
**Start condition:** T-011 done — loop with end_turn/max_tokens handles exits.
**End condition:** When `stop_reason == "tool_use"`, all `tool_use` blocks are dispatched and results sent in one combined `tool_result` message; loop continues.

**Test first:**
- [ ] Run `python agent.py 2>&1 | grep -c "tool_use_id"` — must be ≥ 1 (confirms at least one tool result sent back)
- [ ] Run `python agent.py` and confirm `out.md` is created after the run

**Implementation notes:**
- `elif response.stop_reason == "tool_use":`
- Collect all `tool_use` blocks: `tool_calls = [b for b in response.content if b.type == "tool_use"]`
- Dispatch each: `results = [tools.dispatch(b.name, b.input, b.id) for b in tool_calls]`
- Append single combined message: `messages.append({"role": "user", "content": results})`
- Add comment: `# All tool results must be sent in a single message — Anthropic parallel tool call contract`
- File: `agent.py`

---

### T-013: Implement trace printing

**User story ref:** US-002
**Start condition:** T-012 done — full loop runs.
**End condition:** Stdout shows `--- Step N ---`, `stop_reason`, each tool name + truncated input, each tool result truncated to `MAX_RESULT_CHARS`.

**Test first:**
- [ ] Run `python agent.py 2>&1 | grep -E "^--- Step [0-9]+ ---"` — must match ≥ 1 line
- [ ] Run `python agent.py 2>&1 | grep "stop_reason"` — must match ≥ 1 line
- [ ] Run `python agent.py 2>&1 | grep "tool:"` — must match ≥ 1 line (a tool was called)

**Implementation notes:**
- At top of each loop iteration: `print(f"--- Step {turn} ---")`
- After `client.messages.create`: `print(f"  stop_reason: {response.stop_reason}")`
- For each tool call: `print(f"  tool: {b.name} | input: {str(b.input)[:MAX_RESULT_CHARS]}")`
- For each tool result: `print(f"  result: {r['content'][:MAX_RESULT_CHARS]}")`
- Keep trace prints to single `print()` calls — no logging framework
- File: `agent.py`

---

## Phase 4: Integration & Validation

### T-014: Behaviour validation — run agent end-to-end

**User story ref:** US-001, US-002, US-003, US-006 (all runtime acceptance criteria)
**Start condition:** T-013 done — `agent.py` fully implemented; real `.env` with both API keys.
**End condition:** All 4 shell assertions below pass simultaneously on a single run.

**Test first:**
- [ ] `python agent.py 2>&1 | tee trace.txt && grep -c "^--- Step" trace.txt | awk '$1>=1'` — must produce a number ≥ 1
- [ ] `grep "=== DONE ===" trace.txt` — must match
- [ ] `wc -c < out.md | awk '$1>=100'` — must be ≥ 100 bytes
- [ ] Process exit code: `echo $?` — must be 0

**Implementation notes:**
- This is a live integration test — requires real API keys and internet
- Must be run manually; not part of CI (CI runs unit tests only)
- Record the full trace.txt as evidence of acceptance; keep in `.agent_memory.log`

---

### T-015: Verify `agent.py` ≤ 100 lines

**User story ref:** US-001 (acceptance criterion: "total source lines ≤ 100")
**Start condition:** T-013 done — `agent.py` complete.
**End condition:** `wc -l agent.py` reports ≤ 100.

**Test first:**
- [ ] `wc -l agent.py | awk '{if ($1>100) exit 1}'` — exit code 0 (≤ 100 lines)

**Implementation notes:**
- If over budget: remove blank lines between single-line blocks, collapse constants to one assignment per line
- Do NOT remove comments that explain parallel tool call contract (required by US-007)
- Refactoring strategy: move any helper dicts/strings to `tools.py` if needed

---

## Phase 5: Documentation (`README.md`)

### T-016: Write README with `stop_reason values` section

**User story ref:** US-009
**Start condition:** T-015 done — code is stable.
**End condition:** `README.md` has a `## stop_reason values` section listing all 4 values with meaning + loop action + minimal `if/elif` snippet.

**Test first:**
- [ ] `grep "## stop_reason values" README.md` — must match
- [ ] `grep "end_turn\|tool_use\|max_tokens\|stop_sequence" README.md | wc -l | awk '$1>=4'` — all 4 values present

**Implementation notes:**
- Table or bullet list: `end_turn` → break, `tool_use` → dispatch + continue, `max_tokens` → bail-out, `stop_sequence` → treat as end_turn
- Code snippet: bare-minimum `if/elif` from `agent.py` (can be a copy)
- No value omitted — cross-check against Anthropic API reference

---

### T-017: Add `Parallel tool calls` section to README

**User story ref:** US-010
**Start condition:** T-016 done.
**End condition:** README has `## Parallel tool calls` section ≤ 200 words explaining when, why, and how; includes before/after example.

**Test first:**
- [ ] `grep "## Parallel tool calls" README.md` — must match
- [ ] Word count of section ≤ 200: `awk '/^## Parallel/,/^## /' README.md | wc -w | awk '$1<=200'`

**Implementation notes:**
- Explain: model emits multiple `tool_use` blocks in one response → run all → send all results in ONE `user` message
- "Before" (wrong): one result message per tool call. "After" (correct): one message with array of results
- Reference the comment in `agent.py` line that enforces this

---

### T-018: Add `Tool error handling` section to README

**User story ref:** US-011
**Start condition:** T-017 done.
**End condition:** README has `## Tool error handling` section explaining per-tool catch, `is_error: true`, model retry delegation; includes a concrete trace example for a `web_search` failure.

**Test first:**
- [ ] `grep "## Tool error handling" README.md` — must match
- [ ] `grep "is_error" README.md` — must match (policy explained)
- [ ] Section includes a fenced code block showing example trace output when `web_search` fails

**Implementation notes:**
- Three points: (1) errors caught per-tool in `dispatch()`, (2) returned as `is_error: True` dict, (3) model sees error and decides to retry or pivot — no automatic retry in code
- Concrete trace example (fabricated but accurate to actual output format):
  ```
  --- Step 2 ---
    tool: web_search | input: {'query': 'anthropic engineering blog'}
    result: Error: Tavily – 401 Unauthorized
  --- Step 3 ---
    stop_reason: tool_use  ← model retried with different query
  ```
- Explicitly state: only `web_search` may fail due to network; `read_file`/`write_file` failures are delegated to model with no retry

---

### T-019: Write `README.md` introduction and setup sections

**User story ref:** US-001 (project must be runnable), Architecture § 5 (setup commands)
**Start condition:** T-016–T-018 done (all technical sections exist).
**End condition:** README has title, one-paragraph description, Prerequisites, Installation, and Usage sections with exact commands.

**Test first:**
- [ ] `grep "python agent.py" README.md` — must match
- [ ] `grep "uv venv" README.md` — must match
- [ ] A new reader can clone the repo and run the agent without asking any questions (human review)

**Implementation notes:**
- Prerequisites: Python ≥ 3.12, `uv`, API keys for Anthropic and Tavily
- Installation: `uv venv`, `uv pip install -e ".[dev]"`, `cp .env.example .env` + fill keys
- Usage: `python agent.py`
- Keep it short — the learning value is in the technical sections already written
