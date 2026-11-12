# AgentMemory per-step directive

You MUST use the `agentmemory` MCP server on every step to save tokens. Do not rely on memory alone.

At the START of every step, before doing any work, query agentmemory for relevant prior context:
- Call `memory_recall` or `memory_smart_search` with a query about the current task/files to retrieve past decisions, file history, and lessons.
- Prefer reusing recalled context over re-reading files or re-explaining prior work.

DURING the step, if you learn anything new (a decision, a file change, a pattern, a bug, a fix), keep it in mind to persist.

At the END of every step, after completing work, persist what happened:
- Call `memory_save` with the key insight/decision/outcome, including `type`, `concepts`, `files`, and `project`.
- Set `project` to the current project name.
- If a lesson was learned, also call `memory_lesson_save`.

Goal: every step reads from agentmemory first and writes back after, so context compounds across sessions and token usage drops (less re-reading, less re-explaining).
