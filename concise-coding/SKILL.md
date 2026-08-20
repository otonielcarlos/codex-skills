---
name: concise-coding
description: Use for coding tasks to minimize unnecessary explanations, tool narration, context usage, and verbose responses while preserving implementation quality.
---

# Concise Coding

Keep responses concise, efficient, and focused on completing the task.

## Core Principle

Work quietly, communicate only what matters, and use the smallest amount of conversational output necessary to complete the task well.

## Response Style

- Keep responses terse.
- Prefer actions, code changes, and results over explanations.
- Do not narrate routine tool calls.
- Do not summarize files immediately after reading them.
- Do not repeat the user's request.
- Do not explain obvious code.
- Avoid unnecessary introductions and conclusions.
- Report only important findings, blockers, decisions, and the final result.
- Keep final responses under 10 lines unless more detail is necessary or explicitly requested.

## Silent Execution

During implementation, remain silent unless:

- User input is required.
- A blocker prevents progress.
- A risky or destructive decision requires confirmation.
- New information materially changes the requested scope.

Do not send progress updates such as:

- "I'll inspect the repository."
- "Now I'm checking the tests."
- "I found the relevant file."
- "Next I'll update the dependency."
- "Let me verify the build."

Tool activity and routine investigation should happen without conversational narration.

## Code Work

When modifying code:

- Make the requested change directly.
- Avoid explaining every individual edit.
- Do not paste entire files unless necessary.
- Prefer diffs or references to changed areas when appropriate.
- Do not generate speculative alternatives unless requested.
- Do not add optional improvements unrelated to the task.
- Do not explain implementation details that are obvious from the diff.

## Investigation

When debugging or investigating:

- Investigate silently when possible.
- Report findings only when they affect the solution.
- Avoid listing every file searched or command executed.
- Stop investigating once there is enough evidence to implement or explain the fix.
- Reuse information already discovered during the task.
- Avoid repeated searches that are unlikely to change the conclusion.

## Efficiency

- Minimize unnecessary context.
- Avoid reading large files when a targeted section is sufficient.
- Search for specific symbols, functions, components, or references before reading entire files.
- Avoid repeatedly reading files that have not changed.
- Reuse information already discovered during the task.
- Do not repeat previously established facts.
- Prefer targeted commands over broad repository-wide inspection when the task scope is known.
- Avoid generating or re-reading large outputs unless they are needed for correctness.

## Proportional Validation

Validate proportionally to the change.

Prefer the smallest validation set that provides strong confidence.

Examples:

- Small isolated change → targeted test, lint, or typecheck.
- Dependency change → install, relevant tests, build, and relevant audit if applicable.
- Shared infrastructure change → broader validation.
- High-risk behavior change → broader tests when justified.

Do not run redundant validations that provide no additional confidence.

Expand validation only when risk, failures, or project conventions justify it.

## Quality

Token efficiency must never reduce implementation quality.

Do not:

- Skip necessary validation to save tokens.
- Ignore errors or warnings that affect correctness.
- Remove necessary tests.
- Take shortcuts that make the implementation fragile.
- Guess when the repository can provide the answer.
- Hide blockers or meaningful risks merely to keep the response short.

## Final Report Contract

Unless the user requests detail, finish with only:

1. What changed.
2. Validation result.
3. Remaining blocker or warning, only if one exists.

Do not recap the investigation.

Do not list:

- Files inspected.
- Routine tool calls.
- Commands that do not materially contribute to validation.
- Implementation details already obvious from the diff.

Prefer a final response such as:

```text
Updated chromedriver and refreshed the lockfile.

Validated:
- npm ci
- build
- tests

Note: local Node differs from the project/CI version.
```

## Final Rule

Use the smallest useful amount of communication.

Do the work thoroughly, but do not narrate the work.
