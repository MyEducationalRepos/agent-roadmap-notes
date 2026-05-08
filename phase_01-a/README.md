# Phase 1a — Raw SDK agent

1. Create a new public repo `agent-from-scratch`.
2. Write a tool-using agent in **under 100 lines** using `anthropic.messages.create`.
3. Implement exactly three tools: `web_search` (use Tavily), `read_file`, `write_file`.
4. Run it on this task: *"Summarize the last 5 posts on https://anthropic.com/engineering and save the summary to `out.md`."*
5. Print every step of the trace to stdout.
6. Add `README.md` explaining `stop_reason` values, parallel tool calls, and how you handle tool errors.

- [ ] **Phase 1a deliverable:** repo `agent-from-scratch` with working agent + README.

## stop_reason values

Every `client.messages.create(...)` response carries a `stop_reason` that tells the loop why the model stopped. The agent handles all four values explicitly:

| Value           | Meaning                                                                 | Loop action                                          |
|-----------------|-------------------------------------------------------------------------|------------------------------------------------------|
| `end_turn`      | Model is done answering — no further turn expected.                     | Print `=== DONE ===` and break.                      |
| `tool_use`      | Model emitted one or more `tool_use` blocks and is waiting for results. | Dispatch all tool calls in parallel, append results. |
| `max_tokens`    | Model hit the per-call `max_tokens` cap before finishing its response.  | Print `=== HALT: max_tokens ===` and break.          |
| `stop_sequence` | Model produced a configured stop sequence (none configured here).       | Falls into the unhandled branch and breaks safely.   |

Mapped one-for-one to the loop in `agent.py`:

```python
if response.stop_reason == "end_turn":
    print("=== DONE ===")
    break
elif response.stop_reason == "max_tokens":
    print("=== HALT: max_tokens ===")
    break
elif response.stop_reason == "tool_use":
    # parallel dispatch, see below
    ...
else:
    print(f"=== HALT: unhandled stop_reason {response.stop_reason} ===")
    break
```

## Parallel tool calls

When `stop_reason == "tool_use"`, the assistant message can carry **several** `tool_use` blocks in a single turn — for example, two `web_search` calls plus one `read_file`. The agent treats this as the contract:

1. Append the **whole** assistant message (`response.content`) to the conversation. All `tool_use` blocks must travel together.
2. Run every tool via `dispatch(...)` and collect one `tool_result` per `tool_use_id`.
3. Append a **single** user message whose `content` is the list of all `tool_result` blocks, in the same order.

In code this is one list comprehension:

```python
results = [dispatch(b.name, b.input, b.id) for b in tool_uses]
messages.append({"role": "user", "content": results})
```

Two rules the API enforces:

- Every `tool_use_id` from the assistant turn must have a matching `tool_result` in the next user turn — partial replies raise a 400.
- `tool_result` blocks belong in **one** user message, not several. Splitting them breaks the turn pairing.

The dispatch step itself is sequential here (simple, deterministic logging); for I/O-heavy tools it could be parallelised with threads without changing the message contract.
