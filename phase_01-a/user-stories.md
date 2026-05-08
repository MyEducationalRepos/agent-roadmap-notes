# User Stories

> Generated: 2026-05-08
> Project: agent-from-scratch

---

## Epic: Agent Core Loop

### US-001: Run the agent end-to-end

**As a** learner building my first agentic system,
**I want to** execute the agent with a single command and see it complete a multi-step task,
**so that** I can confirm the full tool-calling loop works before I modify anything.

**Acceptance Criteria:**
- [ ] Running `python agent.py` with no arguments triggers the default task
- [ ] The agent reaches a final answer and prints it to stdout
- [ ] The process exits with code 0 on success
- [ ] The total source lines of `agent.py` do not exceed 100

**INVEST check:** Independent single-file deliverable; negotiable on default task wording; valuable as first proof-of-life; estimable (1–2 hrs); small (one file, one task); testable via exit code and line count.

---

### US-002: Observe every reasoning step in the terminal

**As a** learner tracing agent behaviour,
**I want to** see each model response, every tool call, and every tool result printed to stdout as they happen,
**so that** I can understand exactly what the agent decided at each step without opening a debugger.

**Acceptance Criteria:**
- [ ] Each agentic step prints a numbered header (e.g., `--- Step 1 ---`)
- [ ] The `stop_reason` returned by the API is printed for every model turn
- [ ] Each tool call prints: tool name, input arguments
- [ ] Each tool result prints: tool name, truncated output (≤ 500 chars)
- [ ] No step is silently skipped even when a tool returns an error

**INVEST check:** Independent from tool implementation; negotiable on exact format; valuable for learning; estimable (< 1 hr); small (pure logging); testable by capturing stdout and asserting the expected sections appear.

---

### US-003: Stop gracefully when the agent reaches a final answer

**As a** learner reading agent output,
**I want to** see a clear "DONE" marker when the agent stops iterating,
**so that** I know the task is complete and can find the final answer at the bottom of the trace.

**Acceptance Criteria:**
- [ ] When `stop_reason == "end_turn"` the loop exits and prints `=== DONE ===`
- [ ] The final assistant message is printed in full after the marker
- [ ] The agent does not re-enter the loop after printing `=== DONE ===`
- [ ] If the model never reaches `end_turn` within 10 turns, the agent exits with an informative message

**INVEST check:** Independent from tool logic; negotiable on marker text; valuable (prevents infinite loops); estimable (< 1 hr); small (loop-exit condition only); testable by asserting marker presence in stdout.

---

## Epic: Tool Integration

### US-004: Search the web for current information

**As a** learner testing the agent on live content,
**I want to** give the agent a URL or topic and have it retrieve up-to-date information via Tavily,
**so that** I can see how a real retrieval tool extends the model's knowledge beyond its training cutoff.

**Acceptance Criteria:**
- [ ] `web_search(query)` returns at least one result for any non-empty query string
- [ ] Results include a title and a URL for each hit
- [ ] If Tavily returns an error (e.g., invalid API key), the tool returns a structured error string instead of raising an exception
- [ ] The agent re-plans correctly after receiving a search error

**INVEST check:** Independent of file tools; negotiable on result count; valuable (demonstrates live retrieval); estimable (1–2 hrs); small (one tool); testable via mocked Tavily responses and real smoke test.

---

### US-005: Read a local file during task execution

**As a** learner exploring file-aware agents,
**I want to** instruct the agent to read a file from disk and incorporate its contents into its reasoning,
**so that** I can see how an agent handles persistent local context.

**Acceptance Criteria:**
- [ ] `read_file(path)` returns the full UTF-8 content of an existing file
- [ ] If the file does not exist, the tool returns `"Error: file not found – <path>"` without crashing
- [ ] Paths outside the working directory are accepted (no artificial sandboxing in phase 1a)
- [ ] Binary files return `"Error: not a text file"` rather than garbled bytes

**INVEST check:** Independent of web_search and write_file; negotiable on sandboxing policy; valuable (local context use case); estimable (< 1 hr); small (stdlib only); testable with fixture files.

---

### US-006: Persist agent output to a file

**As a** learner reviewing agent results after a run,
**I want to** have the agent write its final summary to `out.md` automatically,
**so that** I have a durable artifact I can open in any editor without re-running the agent.

**Acceptance Criteria:**
- [ ] `write_file(path, content)` creates or overwrites the file at `path` with `content`
- [ ] The agent calls `write_file` on `out.md` as the final action of the default task
- [ ] After the run, `out.md` exists and contains the summarised content (≥ 100 chars)
- [ ] If the target directory does not exist, the tool returns a descriptive error string

**INVEST check:** Independent of read_file and web_search; negotiable on overwrite vs. append; valuable (durable output); estimable (< 1 hr); small (stdlib only); testable by asserting file existence and content length.

---

### US-007: Use multiple tools in a single model turn

**As a** learner understanding parallel tool execution,
**I want to** see the agent issue two or more tool calls in one turn when it determines they are independent,
**so that** I understand how the Anthropic API supports batched tool use and why it reduces total round-trips.

**Acceptance Criteria:**
- [ ] When the model returns `stop_reason == "tool_use"` with multiple `tool_use` blocks, all tools are executed before the next model call
- [ ] The trace prints each parallel tool call and its result with a shared step label (e.g., `Step 3a`, `Step 3b`)
- [ ] The combined results are sent back in a single `tool_result` message array
- [ ] A comment or docstring in the code explains why parallel calls require a single follow-up message

**INVEST check:** Independent of specific tools; negotiable on label format; valuable (core API concept); estimable (1–2 hrs); small (loop modification only); testable by asserting multi-tool turn appears in trace for appropriate tasks.

---

## Epic: Error Handling

### US-008: Recover from a tool failure without crashing

**As a** learner stress-testing the agent,
**I want to** see the agent continue its reasoning when a tool returns an error,
**so that** I understand how a robust agent handles partial failures rather than silently dying.

**Acceptance Criteria:**
- [ ] Any exception raised inside a tool is caught and converted to a string error result
- [ ] The error result is sent back to the model as a `tool_result` with `is_error: true`
- [ ] The agent's next turn acknowledges the failure and either retries or picks an alternative approach
- [ ] The process never raises an unhandled exception due to a tool error

**INVEST check:** Independent; negotiable on retry policy; valuable (robustness lesson); estimable (< 1 hr); small (try/except wrapper); testable by injecting a failing tool mock.

---

## Epic: Documentation & Knowledge Transfer

### US-009: Understand stop_reason semantics from the README

**As a** learner reading the project README,
**I want to** find a clear explanation of every `stop_reason` value the Anthropic API can return,
**so that** I know how to branch my agent loop correctly for each case without reading the full API reference.

**Acceptance Criteria:**
- [ ] README has a dedicated section titled `stop_reason values`
- [ ] Each value (`end_turn`, `tool_use`, `max_tokens`, `stop_sequence`) is listed with a one-line meaning and the correct loop action to take
- [ ] A code snippet shows the minimal `if/elif` branch for handling all four values
- [ ] No value is omitted or described incorrectly

**INVEST check:** Independent of code changes; negotiable on snippet language; valuable (conceptual clarity); estimable (30 min); small (one README section); testable by diff against official API docs.

---

### US-010: Learn how parallel tool calls work from the README

**As a** learner new to the tool-use API,
**I want to** read a plain-English explanation of parallel tool calls in the README,
**so that** I can reproduce the pattern in my own projects without trial and error.

**Acceptance Criteria:**
- [ ] README has a section titled `Parallel tool calls`
- [ ] The section explains: when the model emits multiple `tool_use` blocks, why they should all run before the next model call, and how to assemble the `tool_result` array
- [ ] A minimal before/after example (sequential vs. parallel) is included
- [ ] The explanation is ≤ 200 words

**INVEST check:** Independent; negotiable on example format; valuable; estimable (30 min); small (one README section); testable by reading comprehension checklist.

---

### US-011: Know how tool errors are handled before submitting a task

**As a** learner about to run the agent on a flaky network,
**I want to** read the README's tool-error policy before I start,
**so that** I can predict what will happen if Tavily is down or a file path is wrong without being surprised.

**Acceptance Criteria:**
- [ ] README has a section titled `Tool error handling`
- [ ] The section explains: errors are caught per-tool, returned as `is_error: true` results, and the model decides whether to retry
- [ ] One concrete example shows what the trace looks like when `web_search` fails
- [ ] The section explicitly states which errors are retried automatically vs. delegated to the model

**INVEST check:** Independent; negotiable on retry examples; valuable (operational clarity); estimable (30 min); small (one README section); testable by comparing README to actual error-handling code.
