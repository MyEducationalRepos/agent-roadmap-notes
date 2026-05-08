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
