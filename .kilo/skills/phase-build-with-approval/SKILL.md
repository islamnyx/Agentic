# Kilo Skill: Phase-by-Phase Build with Approval

## Purpose

Work through the Agent OS MVP one phase at a time. Never mark a todo as complete without your approval. Always write tests for every task. Explain changes at an intermediate level (clear, not overly academic).

## Workflow (always follow this order)

### Step 1: Pick the next unchecked todo
Read `technical/todo.md`. Find the first `[ ]` item in the current phase. Do not skip ahead.

### Step 2: Implement the code
Write the code needed for that one todo item. Keep it simple and focused. Do not build ahead of the todo list.

### Step 3: Write tests
Add tests for the new code in `gateway/tests/`. Tests must pass before moving on.

### Step 4: Run all tests
Run `pytest tests/` in `gateway/`. All tests must pass (100% green). Fix any failures.

### Step 5: Explain at intermediate level
Summarize what you built in plain terms — like explaining to a student who knows basic Python but isn't an expert. Cover:
- What files were created/changed
- What each piece does
- How it fits into the bigger picture
- Why we chose this approach

### Step 6: Ask for approval
Stop and ask the user: "I've completed [task] with tests passing. Shall I check it off the todo list?" Wait for their yes/no before editing `todo.md`.

### Step 7: Check off the todo
Only after the user says yes, change `[ ]` to `[x]` in `technical/todo.md`.

## Rules

- One todo item at a time. Do not batch multiple items.
- Tests are mandatory. No tests = not done.
- All existing tests must still pass after each change.
- Intermediate-level explanations only. Avoid jargon without explaining it.
- Always ask before checking off. Never auto-check.

## Files involved

- `technical/todo.md` — the master checklist (only edit after approval)
- `gateway/gateway/` — the application code
- `gateway/tests/` — the test code
- `docker-compose.yml` — infrastructure services
