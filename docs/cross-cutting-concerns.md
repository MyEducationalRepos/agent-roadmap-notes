# Cross-Cutting Concerns — agent-from-scratch (Phase 1a)

> Scope: single-file CLI agent, `agent.py` ≤ 100 lines, Python 3.12, uv, no server, no DB.

---

## 1. Security Posture

### 1.1 API Key Management

| Rule | Detail |
|------|--------|
| Keys never in source | `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` are loaded via `python-dotenv` from `.env` at startup |
| `.env` gitignored | Add `.env` to `.gitignore` **before** the first commit |
| `.env.example` committed | Commit a sanitised template so contributors know which variables are required |

```
# .env.example  (committed)
ANTHROPIC_API_KEY=sk-ant-...replace-me...
TAVILY_API_KEY=tvly-...replace-me...
```

```
# .gitignore  (must include)
.env
```

Validation at startup:

```python
import os
from dotenv import load_dotenv

load_dotenv()

_required = ("ANTHROPIC_API_KEY", "TAVILY_API_KEY")
for var in _required:
    if not os.getenv(var):
        raise SystemExit(f"Missing required environment variable: {var}")
```

### 1.2 `write_file` — Path Traversal Risk

`write_file(path, content)` accepts arbitrary paths, which means the model can instruct the agent to overwrite files outside the current working directory (e.g., `../../~/.bashrc`).

**Phase 1a decision:** this is a **known, intentional limitation** documented in the README. No sandbox is enforced because the agent runs locally under the operator's own credentials, and adding path validation would add complexity that obscures the teaching goal.

**Mitigation note for README:**

> ⚠️ `write_file` performs no path validation in phase 1a. Never run this agent against an untrusted prompt in a production environment. A future phase will add a `SAFE_DIR` allowlist.

### 1.3 `read_file` — No Sandboxing (Intentional)

Per US-005: paths outside the working directory are accepted. The rationale is pedagogical: the phase 1a agent must be able to read existing files anywhere on the operator's machine to demonstrate realistic file-aware reasoning.

Document explicitly in README:

> `read_file` has no path restriction in phase 1a. This is intentional: the goal is to show a working file-aware agent, not a hardened one.

---

## 2. Observability

### 2.1 Stdout as the Observability Layer

Phase 1a has no logging framework, metrics, or tracing backend. **Stdout is the sole observability surface.** This is a deliberate choice: it keeps `agent.py` under 100 lines and makes the control flow visible to learners with zero tooling setup.

### 2.2 Trace Line Semantics

Every `print` call carries a specific meaning. The table below is the contract:

| Trace line | What it communicates |
|---|---|
| `--- Step N ---` | A new agentic turn begins; N is 1-based and monotonically increasing |
| `stop_reason: <value>` | Why the model stopped generating (see §7 README outline for the full table) |
| `[tool_call] <name>(<args>)` | The model is requesting a tool; args are printed as a dict, truncated to 200 chars |
| `[tool_result] <name>: <snippet>` | The tool's return value, truncated to 500 chars (per US-002) |
| `=== DONE ===` | `stop_reason == "end_turn"` reached; loop exits after this line |
| `[error] step N exceeded turn limit` | The agent exhausted the 10-turn guard and exited (per US-003) |

Example trace fragment:

```
--- Step 1 ---
stop_reason: tool_use
[tool_call] web_search({'query': 'anthropic engineering blog'})
[tool_result] web_search: {'title': 'Anthropic Engineering', 'url': 'https://...'}

--- Step 2 ---
stop_reason: tool_use
[tool_call] write_file({'path': 'out.md', 'content': '# Summary\n...'})
[tool_result] write_file: ok

--- Step 3 ---
stop_reason: end_turn
=== DONE ===
The summary has been saved to out.md.
```

### 2.3 Redirecting Trace Output

| Goal | Shell command |
|---|---|
| Suppress trace, keep final answer | `python agent.py 2>/dev/null` *(stdout only)* |
| Save full trace to file | `python agent.py \| tee run.log` |
| Separate trace from stderr | All trace goes to stdout; add `file=sys.stderr` to trace prints if you want separation |
| Timestamped trace | `python agent.py \| ts '[%H:%M:%S]' \| tee run.log` *(requires `moreutils`)* |

---

## 3. Scalability Trade-offs

### 3.1 Single-Turn CLI Script

Phase 1a is a **one-shot script**, not a server. Concepts like horizontal scaling, connection pooling, and request queuing are out of scope. Do not add any server infrastructure.

### 3.2 Context Window Growth

The `messages` list accumulates every turn:

```
[system, user, assistant(step1), tool_results(step1), assistant(step2), ...]
```

For the default task (≤ 10 turns, ≤ ~50k tokens total), this is well within Claude's context window. **No summarisation, compaction, or eviction is needed in phase 1a.**

| Scenario | Token estimate | Risk |
|---|---|---|
| Default task, ≤ 10 turns | ~5k–20k | None |
| Scraped pages injected via `read_file` | +8k per file | Low; watch total |
| > 20 turns | > 40k | Approach window limit; defer to phase 2 |

Phase 2 will introduce context compaction (summarise earlier turns) and episodic memory (vector store).

### 3.3 Tavily Rate Limits

Tavily free tier: **1 000 API calls/month**. The default task uses 2–4 calls. No rate-limit handling is required in phase 1a.

Document in README:

> Tavily free tier allows 1 000 searches/month. Each agent run uses 2–4 searches. If you hit the limit, `web_search` returns an error string and the agent will attempt to proceed without search results.

---

## 4. Docker Image Design

**Phase 1a: no Docker.** A `uv`-managed virtual environment is sufficient:

```bash
uv venv
uv pip install -e .
python agent.py
```

**Future phase note** (for README "Roadmap" section):

> A phase 1b container would use `python:3.12-slim` as base, copy only `agent.py`, `pyproject.toml`, and `.env.example`, and set `ENTRYPOINT ["python", "agent.py"]`. Total image size target: < 200 MB.

No `docker-compose`, no multi-stage build, no orchestration in scope until a server is introduced (phase 3).

---

## 5. `pyproject.toml` Design

Canonical file managed by `uv`:

```toml
[project]
name = "agent-from-scratch"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.25",
    "tavily-python>=0.3",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]
```

> **Note:** `[tool.uv].dev-dependencies` and `[project.optional-dependencies].dev` are redundant when using `uv` exclusively. Keep only `[tool.uv]` to avoid duplication — `uv add --dev` writes there by default.

Install commands:

```bash
uv pip install -e .            # runtime only
uv pip install -e ".[dev]"     # with test deps
# or with uv sync:
uv sync --extra dev
```

---

## 6. Long-Term Evolution

### Phase 1b — Framework Migration

Swap the raw `anthropic.messages.create` loop for a higher-level SDK (Anthropic Agents SDK or similar) once the learner understands what the framework abstracts. The tool definitions, `.env` loading, and pyproject layout remain unchanged. Target: same < 100 line budget.

### Phase 2 — Extended Capabilities

| Addition | Detail |
|---|---|
| Semantic memory | Embed tool results and prior turns into a vector store (e.g., `chromadb` or `faiss`) |
| Streaming output | Switch to `anthropic.messages.stream()` for real-time token display |
| Additional tools | `code_exec`, `browser`, `calendar` |
| Context compaction | Summarise early turns when `len(messages) > threshold` |

### Phase 3 — Server Wrapping

Wrap `agent.py` in a **FastAPI** server:

- `POST /run` accepts `{ "task": "..." }` and streams the trace over SSE (Server-Sent Events)
- `GET /runs/{id}` returns the stored trace
- Add `SAFE_DIR` enforcement for `write_file`
- Introduce proper structured logging (`structlog` or `loguru`) replacing stdout traces
- Deploy with a `python:3.12-slim` Docker image behind a reverse proxy

---

## 7. README Outline

The README for `agent-from-scratch` must contain exactly these sections, in order:

### 7.1 Quick Start
```
git clone ...
cd agent-from-scratch
cp .env.example .env   # fill in keys
uv venv && uv pip install -e .
python agent.py
```

### 7.2 `stop_reason` Values

| Value | Meaning | Loop action |
|---|---|---|
| `"end_turn"` | Model finished its response naturally | Exit loop, print `=== DONE ===` |
| `"tool_use"` | Model wants to call one or more tools | Execute all tool calls, append results, loop |
| `"max_tokens"` | Response was cut off at the token limit | Treat as partial; optionally continue or abort |
| `"stop_sequence"` | A custom stop sequence was matched | Exit loop (not used in phase 1a) |

Minimal branch:

```python
if stop_reason == "end_turn":
    break
elif stop_reason == "tool_use":
    # execute tools, append results, continue
elif stop_reason == "max_tokens":
    print("[warn] max_tokens reached — response may be truncated")
    break
```

### 7.3 Parallel Tool Calls

When the model returns `stop_reason == "tool_use"`, the response may contain **multiple `tool_use` blocks** in a single turn. This happens when the model determines that two or more tool calls are independent and can be resolved simultaneously.

The implementation must:
1. Iterate over **all** `tool_use` blocks in the response before making the next API call.
2. Collect every result into a single `tool_results` message array.
3. Send that array as **one** user message — not one message per result.

Sending separate messages per result is an API error.

```python
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        result = dispatch_tool(block.name, block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        })
messages.append({"role": "user", "content": tool_results})
```

### 7.4 Tool Error Handling Policy

| Situation | Behaviour |
|---|---|
| Tool raises an exception | Caught, converted to `"Error: <message>"` string |
| Result sent to model | As `tool_result` with `is_error: true` |
| Model response | Acknowledges failure; retries, uses alternative tool, or gives up gracefully |
| Process behaviour | Never raises unhandled exception due to tool error |

### 7.5 Known Limitations (Phase 1a)

- `write_file` has no path traversal protection. Run only with trusted prompts.
- `read_file` has no sandboxing. The agent can read any file the OS user can access.
- No retry logic for Anthropic or Tavily API failures.
- Single-session only; no memory between runs.
- Tavily free tier: 1 000 calls/month.

### 7.6 Roadmap

Brief bullets pointing to phases 1b → 2 → 3 (see §6 above).

---

*Document version: 2026-05-08 · Phase 1a*
