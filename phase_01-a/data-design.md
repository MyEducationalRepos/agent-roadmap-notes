# Data & State Design — agent-from-scratch

> Role: Database Designer Agent
> Scope: Phase 1a — no persistent DB; all state is in-memory + filesystem.

---

## 1. In-Memory State Schema

The agent's entire runtime state lives in a single `messages` list passed to
`anthropic.messages.create`. No globals, no side-channel state.

```python
from typing import Literal, TypedDict, Union

# ── Primitive content blocks ────────────────────────────────────────────────

class TextBlock(TypedDict):
    type: Literal["text"]
    text: str                        # model prose or user instruction

class ToolUseBlock(TypedDict):
    type: Literal["tool_use"]
    id: str                          # e.g. "toolu_01XYZ…"  (Anthropic-assigned)
    name: Literal["web_search", "read_file", "write_file"]
    input: dict[str, str]            # tool-specific kwargs (see §3)

class ToolResultBlock(TypedDict):
    type: Literal["tool_result"]
    tool_use_id: str                 # must match a preceding ToolUseBlock.id
    content: str                     # serialised result string (see §3)
    is_error: bool                   # True when the tool raised / returned an error

# ── Message rows ─────────────────────────────────────────────────────────────

class UserMessage(TypedDict):
    role: Literal["user"]
    content: Union[
        str,                                           # initial task prompt
        list[ToolResultBlock],                         # tool results returned to model
    ]

class AssistantMessage(TypedDict):
    role: Literal["assistant"]
    content: list[Union[TextBlock, ToolUseBlock]]      # mix of prose + tool calls

# ── Top-level container ───────────────────────────────────────────────────────

Messages = list[Union[UserMessage, AssistantMessage]]
```

### Growth pattern per turn

```
turn 0  → UserMessage        (task string)
turn 1  → AssistantMessage   (TextBlock* + ToolUseBlock*)
turn 2  → UserMessage        (list[ToolResultBlock])   ← one per tool called in turn 1
turn 3  → AssistantMessage   …
…
turn N  → AssistantMessage   (stop_reason == "end_turn", TextBlock only)
```

**Invariant:** every `ToolUseBlock.id` in an `AssistantMessage` must appear as a
`ToolResultBlock.tool_use_id` in the very next `UserMessage`.
The API enforces this; violating it returns a 400.

---

## 2. Filesystem Schema

### Files the agent reads

| Path pattern | Encoding | Notes |
|---|---|---|
| Any path supplied by the model to `read_file` | UTF-8 | Binary files return an error string, not bytes |
| `.env` | ASCII-safe | Loaded once at startup via `python-dotenv` |

### Files the agent writes

| Path | Encoding | Created by | Overwrite policy |
|---|---|---|---|
| `out.md` | UTF-8, LF line endings | `write_file` tool | Always overwrite (phase 1a has no append mode) |

### Naming conventions

- All paths are relative to the **process working directory** (where `python agent.py` is run).
- No path sanitisation in phase 1a (per US-005 acceptance criteria).
- `out.md` is the canonical output filename; the model is instructed to use it in the system prompt.

### Encoding guarantees

| Guarantee | Applies to |
|---|---|
| All content written via `write_file` is encoded as UTF-8 | `out.md` |
| All content read via `read_file` is decoded as UTF-8; non-UTF-8 files return an error | any `read_file` call |
| `.env` values are stripped of surrounding whitespace and quotes | env vars |

---

## 3. Tool Result Data Contracts

All three tools return `str`. Errors are also `str` (never exceptions propagated
to the caller). The harness wraps each return value in a `ToolResultBlock`.

### `web_search`

```python
def web_search(query: str) -> str:
    ...
```

**Input schema**

| Key | Type | Required | Description |
|---|---|---|---|
| `query` | `str` | yes | Free-text search query |

**Success return** — newline-separated records, each formatted as:

```
[1] Title: <title>
    URL:   <url>
    Snippet: <snippet>

[2] …
```

Minimum 1 result; maximum `TAVILY_MAX_RESULTS` results (default 5).

**Error return** (is_error = True)

```
Error: web_search failed – <Tavily error message>
```

---

### `read_file`

```python
def read_file(path: str) -> str:
    ...
```

**Input schema**

| Key | Type | Required | Description |
|---|---|---|---|
| `path` | `str` | yes | Relative or absolute filesystem path |

**Success return** — raw UTF-8 content of the file (no length cap in phase 1a).

**Error returns** (is_error = True)

| Condition | Return string |
|---|---|
| File does not exist | `"Error: file not found – <path>"` |
| Path is a directory | `"Error: path is a directory – <path>"` |
| Decode failure (binary) | `"Error: not a text file – <path>"` |
| Permission denied | `"Error: permission denied – <path>"` |

---

### `write_file`

```python
def write_file(path: str, content: str) -> str:
    ...
```

**Input schema**

| Key | Type | Required | Description |
|---|---|---|---|
| `path` | `str` | yes | Target file path (relative or absolute) |
| `content` | `str` | yes | Full file content to write (UTF-8) |

**Success return**

```
OK: wrote <N> bytes to <path>
```

**Error returns** (is_error = True)

| Condition | Return string |
|---|---|
| Parent directory does not exist | `"Error: directory does not exist – <parent>"` |
| Permission denied | `"Error: permission denied – <path>"` |

---

## 4. Message Accumulation Strategy

For a **single short task** (summarise 5 blog posts → write `out.md`) the
full conversation fits comfortably inside the 200 k-token context window.
No truncation or summarisation is required in phase 1a.

### Expected turn count

| Turn | Role | Content |
|---|---|---|
| 0 | user | Task prompt (~50 tokens) |
| 1 | assistant | Plan + 1–3 `web_search` calls |
| 2 | user | Search results (~2 000–4 000 tokens) |
| 3 | assistant | 1 `read_file` or more `web_search` calls |
| 4 | user | File/search results |
| 5 | assistant | `write_file` call with composed summary |
| 6 | user | `write_file` result ("OK: wrote N bytes") |
| 7 | assistant | `end_turn` — final prose confirmation |

**Estimated peak token count:** < 12 000 tokens (well under the 200 k limit).

### Hard-stop guard

A `max_turns: int = 10` counter prevents infinite loops regardless of context
size. When `turns >= max_turns` the loop exits with:

```
Agent did not reach end_turn within {max_turns} turns. Exiting.
```

### Context budget rule (phase 1a)

> If the task is ever extended to require many web searches, truncate each
> tool result to `MAX_RESULT_CHARS = 4000` characters before appending to
> `messages`. This keeps a 20-turn conversation under 100 k tokens.
> Not enforced in phase 1a but the constant should be defined for forward
> compatibility.

---

## 5. Environment Variable Schema

Loaded from `.env` at startup via `python-dotenv`. Never committed to git.

### Required

| Variable | Python type | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | `str` | Anthropic API key. Format: `sk-ant-…` |
| `TAVILY_API_KEY` | `str` | Tavily search API key. Format: `tvly-…` |

Startup fails immediately with a clear `ValueError` if either is absent.

### Optional

| Variable | Python type | Default | Description |
|---|---|---|---|
| `MODEL` | `str` | `"claude-opus-4-5"` | Anthropic model ID |
| `MAX_TOKENS` | `int` | `4096` | `max_tokens` passed to `messages.create` |
| `MAX_TURNS` | `int` | `10` | Hard loop limit before forced exit |
| `TAVILY_MAX_RESULTS` | `int` | `5` | Max results per `web_search` call |
| `LOG_LEVEL` | `str` | `"INFO"` | Python logging level (`DEBUG`, `INFO`, `WARNING`) |

### Validation at startup

```python
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or \
    (_ for _ in ()).throw(ValueError("ANTHROPIC_API_KEY is not set"))

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY") or \
    (_ for _ in ()).throw(ValueError("TAVILY_API_KEY is not set"))

MODEL             = os.environ.get("MODEL", "claude-opus-4-5")
MAX_TOKENS        = int(os.environ.get("MAX_TOKENS", "4096"))
MAX_TURNS         = int(os.environ.get("MAX_TURNS", "10"))
TAVILY_MAX_RESULTS = int(os.environ.get("TAVILY_MAX_RESULTS", "5"))
```

---

## 6. `out.md` Format

### Purpose

Durable, human-readable summary of the task result. Written by the agent as
its last action; consumed by the learner via any Markdown viewer.

### Structure

```markdown
# Anthropic Engineering Blog — Summary

> Generated: YYYY-MM-DD
> Source: https://anthropic.com/engineering

---

## 1. <Post Title>

**URL:** <post URL>

<2–4 sentence summary of the post>

---

## 2. <Post Title>

…

---

## 5. <Post Title>

…

---

*Summary generated by agent-from-scratch (Phase 1a)*
```

### Encoding & size expectations

| Property | Value |
|---|---|
| Encoding | UTF-8, no BOM |
| Line endings | LF (`\n`) |
| Typical size for 5-post summary | 1 200 – 2 500 bytes |
| Minimum size (acceptance criterion from US-006) | 100 bytes |
| Maximum practical size | ~8 000 bytes (no artificial cap in phase 1a) |

### Overwrite semantics

`write_file` **always overwrites** `out.md`. Re-running the agent produces a
fresh file. There is no append mode, versioning, or backup in phase 1a.
If append-on-rerun is needed in a later phase, introduce a `WRITE_MODE` env var
(`overwrite` \| `append`) at that point.
